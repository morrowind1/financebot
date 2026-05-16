import math
import asyncio
import io
from datetime import datetime
from aiogram import Router, F
from aiogram.filters import Command
from aiogram.types import Message, CallbackQuery, BufferedInputFile, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.fsm.context import FSMContext
import matplotlib.pyplot as plt
import pandas as pd

import database as db
import keyboards as kb
from states import BudgetStates, ExpenseStates, GoalStates
from utils import get_days_until_payday, format_history_row

router = Router()

async def generate_status_message(user_id: int) -> str:
    settings = await db.get_user_settings(user_id)
    budget = settings["budget"]
    spent = await db.get_monthly_spent(user_id)
    
    payday_day = settings["payday"]
    payday_month = settings["payday_month"] if settings["payday_month"] > 0 else None
    
    days_left = get_days_until_payday(payday_day, payday_month)
    balance = budget - spent
    
    today_str = datetime.now().strftime("%Y-%m-%d")
    spent_today = 0
    async with db.aiosqlite.connect(db.DB_NAME) as conn:
        async with conn.execute("SELECT SUM(amount) FROM expenses WHERE user_id = ? AND date LIKE ?", (user_id, f"{today_str}%")) as c:
            row = await c.fetchone()
            spent_today = row[0] if row[0] else 0

    if days_left > 0:
        morning_balance = balance + spent_today
        daily_limit = morning_balance / days_left
        rem_today = daily_limit - spent_today
    else:
        rem_today = balance

    return (
        f"💳 <b>статус:</b>\n"
        f"💰 баланс: <b>{balance:.2f} zl</b>\n"
        f"🗓 до зп: <b>{days_left} дн.</b>\n"
        f"💵 на сегодня: <b>{max(0, rem_today):.2f} zl</b>"
    )

@router.message(Command("start"))
async def cmd_start(message: Message, state: FSMContext):
    await state.clear()
    status = await generate_status_message(message.from_user.id)
    await message.answer(f"привет! кошелек под контролем.\n\n{status}", reply_markup=kb.get_main_keyboard(), parse_mode="html")

@router.message(F.text == "💰 бюджет")
async def set_budget_start(message: Message, state: FSMContext):
    await state.set_state(BudgetStates.waiting_for_budget)
    await message.answer("введи общую сумму бюджета:", reply_markup=kb.get_cancel_keyboard())

@router.message(BudgetStates.waiting_for_budget)
async def set_budget_fin(message: Message, state: FSMContext):
    if message.text == "❌ отмена":
        await state.clear()
        return await message.answer("отменено", reply_markup=kb.get_main_keyboard())
    try:
        amount = float(message.text.replace(',', '.'))
        await db.set_user_budget(message.from_user.id, amount)
        await state.clear()
        status = await generate_status_message(message.from_user.id)
        await message.answer(f"бюджет: {amount} zl\n\n{status}", reply_markup=kb.get_main_keyboard(), parse_mode="html")
    except: await message.answer("введи число!")

@router.message(F.text == "🗓 день зп")
async def set_p_start(message: Message, state: FSMContext):
    await state.set_state(BudgetStates.waiting_for_payday)
    await message.answer("введи число месяца (1-31):", reply_markup=kb.get_cancel_keyboard())

@router.message(BudgetStates.waiting_for_payday)
async def set_p_day(message: Message, state: FSMContext):
    if message.text == "❌ отмена":
        await state.clear()
        return await message.answer("отменено", reply_markup=kb.get_main_keyboard())
    try:
        day = int(message.text)
        if not (1 <= day <= 31): raise ValueError()
        await state.update_data(day=day)
        await state.set_state(BudgetStates.waiting_for_month)
        await message.answer("введи номер месяца (1-12) или '0' если каждый месяц:")
    except: await message.answer("введи число от 1 до 31!")

@router.message(BudgetStates.waiting_for_month)
async def set_p_fin(message: Message, state: FSMContext):
    if message.text == "❌ отмена":
        await state.clear()
        return await message.answer("отменено", reply_markup=kb.get_main_keyboard())
    try:
        month = int(message.text)
        data = await state.get_data()
        await db.set_user_payday_full(message.from_user.id, data['day'], month)
        await state.clear()
        status = await generate_status_message(message.from_user.id)
        await message.answer(f"день зп сохранен!\n\n{status}", reply_markup=kb.get_main_keyboard(), parse_mode="html")
    except: await message.answer("введи номер месяца!")

@router.message(F.text == "➕ добавить трату")
async def add_exp_start(message: Message, state: FSMContext):
    await state.set_state(ExpenseStates.waiting_for_amount)
    await message.answer("сколько потратил?", reply_markup=kb.get_cancel_keyboard())

@router.message(ExpenseStates.waiting_for_amount)
async def add_exp_amt(message: Message, state: FSMContext):
    if message.text == "❌ отмена":
        await state.clear()
        return await message.answer("отменено", reply_markup=kb.get_main_keyboard())
    try:
        amount = float(message.text.replace(',', '.'))
        await state.update_data(amount=amount)
        await state.set_state(ExpenseStates.waiting_for_category)
        await message.answer("категория:", reply_markup=kb.get_categories_keyboard())
    except: await message.answer("введи число!")

@router.message(ExpenseStates.waiting_for_category)
async def add_exp_cat(message: Message, state: FSMContext):
    if message.text == "❌ отмена":
        await state.clear()
        return await message.answer("отменено", reply_markup=kb.get_main_keyboard())
    
    category = message.text
    data = await state.get_data()
    amount = data['amount']
    user_id = message.from_user.id
    
    await db.add_expense(user_id, amount, "трата", category)
    
    settings = await db.get_user_settings(user_id)
    round_msg = ""
    if settings.get("auto_round") and category != "🎁 копилка":
        rounding = math.ceil(amount) - amount
        if rounding > 0:
            goals = await db.get_goals(user_id)
            if goals:
                goal_id, goal_title = goals[0][0], goals[0][1]
                await db.update_goal_amount(goal_id, rounding)
                await db.add_expense(user_id, rounding, f"автокопилка: {goal_title}", "🎁 копилка")
                round_msg = f"\n\n✨ {rounding:.2f} zl ушло в копилку '{goal_title}'"

    await state.clear()
    status = await generate_status_message(user_id)
    await message.answer(f"записано: {amount:.2f} zl{round_msg}\n\n{status}", reply_markup=kb.get_main_keyboard(), parse_mode="html")

@router.message(F.text == "🎁 копилка")
async def cmd_goals(message: Message):
    goals = await db.get_goals(message.from_user.id)
    if not goals:
        text = "у тебя пока нет целей. создай новую!"
    else:
        text = "🎯 <b>твои цели:</b>\n\n"
        for _, title, target, current in goals:
            perc = (current / target) * 100 if target > 0 else 0
            text += f"▪️ {title}: <b>{current:.2f}</b> / {target:.2f} zl ({perc:.1f}%)\n"
    
    await message.answer(text, reply_markup=kb.get_goals_keyboard(), parse_mode="html")

@router.callback_query(F.data == "goal_add")
async def goal_add_start(callback: CallbackQuery, state: FSMContext):
    await state.set_state(GoalStates.waiting_for_title)
    await callback.message.answer("введи название цели (например: на отпуск):", reply_markup=kb.get_cancel_keyboard())
    await callback.answer()

@router.message(GoalStates.waiting_for_title)
async def goal_add_title(message: Message, state: FSMContext):
    if message.text == "❌ отмена":
        await state.clear()
        return await message.answer("отменено", reply_markup=kb.get_main_keyboard())
    await state.update_data(title=message.text)
    await state.set_state(GoalStates.waiting_for_target)
    await message.answer("какая сумма нужна?")

@router.message(GoalStates.waiting_for_target)
async def goal_add_fin(message: Message, state: FSMContext):
    if message.text == "❌ отмена":
        await state.clear()
        return await message.answer("отменено", reply_markup=kb.get_main_keyboard())
    try:
        target = float(message.text.replace(',', '.'))
        data = await state.get_data()
        await db.add_goal(message.from_user.id, data['title'], target)
        await state.clear()
        await message.answer(f"цель '{data['title']}' создана!", reply_markup=kb.get_main_keyboard())
    except: await message.answer("введи число!")

@router.callback_query(F.data == "goal_deposit")
async def goal_dep_start(callback: CallbackQuery, state: FSMContext):
    goals = await db.get_goals(callback.from_user.id)
    if not goals: 
        await callback.answer("сначала создай цель!")
        return
    
    await state.update_data(goal_id=goals[0][0], goal_title=goals[0][1])
    await state.set_state(GoalStates.waiting_for_deposit)
    await callback.message.answer(f"сколько отложим в '{goals[0][1]}'?", reply_markup=kb.get_cancel_keyboard())
    await callback.answer()

@router.message(GoalStates.waiting_for_deposit)
async def goal_dep_fin(message: Message, state: FSMContext):
    if message.text == "❌ отмена":
        await state.clear()
        return await message.answer("отменено", reply_markup=kb.get_main_keyboard())
    try:
        amount = float(message.text.replace(',', '.'))
        data = await state.get_data()
        await db.update_goal_amount(data['goal_id'], amount)
        await db.add_expense(message.from_user.id, amount, f"пополнение: {data['goal_title']}", "🎁 копилка")
        await state.clear()
        status = await generate_status_message(message.from_user.id)
        await message.answer(f"отложено {amount} zl!\n\n{status}", reply_markup=kb.get_main_keyboard(), parse_mode="html")
    except: await message.answer("введи число!")

@router.callback_query(F.data == "goal_delete")
async def goal_delete_list(callback: CallbackQuery):
    goals = await db.get_goals(callback.from_user.id)
    if not goals: 
        await callback.answer("целей нет")
        return
    
    builder = InlineKeyboardMarkup(inline_keyboard=[])
    for g_id, title, _, _ in goals:
        builder.inline_keyboard.append([InlineKeyboardButton(text=f"🗑 {title}", callback_data=f"del_goal_{g_id}")])
    
    await callback.message.answer("какую цель удалить?", reply_markup=builder)
    await callback.answer()

@router.callback_query(F.data.startswith("del_goal_"))
async def goal_delete_confirm(callback: CallbackQuery):
    goal_id = int(callback.data.split("_")[-1])
    await db.delete_goal(goal_id)
    await callback.message.edit_text("цель удалена!")
    await callback.answer()

@router.message(F.text == "⚙️ настройки")
async def cmd_settings(message: Message):
    settings = await db.get_user_settings(message.from_user.id)
    round_status = "🟢" if settings['auto_round'] else "🔴"
    
    markup = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=f"{round_status} автокопилка", callback_data="toggle_round")],
        [InlineKeyboardButton(text="🗑 очистить всё", callback_data="confirm_clear")]
    ])
    await message.answer("настройки бота:", reply_markup=markup)

@router.callback_query(F.data == "toggle_round")
async def cb_toggle_round(callback: CallbackQuery):
    settings = await db.get_user_settings(callback.from_user.id)
    new_status = 0 if settings["auto_round"] else 1
    await db.set_auto_round(callback.from_user.id, new_status)
    
    round_status = "🟢" if new_status else "🔴"
    markup = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=f"{round_status} автокопилка", callback_data="toggle_round")],
        [InlineKeyboardButton(text="🗑 очистить всё", callback_data="confirm_clear")]
    ])
    await callback.message.edit_reply_markup(reply_markup=markup)
    await callback.answer(f"автокопилка {'включена' if new_status else 'выключена'}")

@router.callback_query(F.data == "confirm_clear")
async def cb_confirm_clear(callback: CallbackQuery):
    markup = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="✅ ДА, УДАЛИТЬ", callback_data="clear_data_final")],
        [InlineKeyboardButton(text="❌ ОТМЕНА", callback_data="cancel_clear")]
    ])
    await callback.message.edit_text("вы уверены? это удалит все траты и обнулит копилки!", reply_markup=markup)
    await callback.answer()

@router.callback_query(F.data == "cancel_clear")
async def cb_cancel_clear(callback: CallbackQuery):
    await callback.message.delete()
    await callback.message.answer("удаление отменено.", reply_markup=kb.get_main_keyboard())
    await callback.answer()

@router.callback_query(F.data == "clear_data_final")
async def cb_clear_data_final(callback: CallbackQuery):
    user_id = callback.from_user.id
    await db.clear_user_data(user_id)
    status = await generate_status_message(user_id)
    await callback.message.edit_text("✅ данные успешно очищены!\n\n" + status, parse_mode="html")
    await callback.answer()

@router.message(F.text == "📊 история")
async def cmd_history(message: Message):
    expenses = await db.get_all_expenses_report(message.from_user.id)
    if not expenses: return await message.answer("история пуста")
    report = "📋 <b>последние траты:</b>\n\n"
    for row in expenses[:15]:
        report += format_history_row(row) + "\n"
    await message.answer(report, parse_mode="html")

@router.message(F.text == "🔄 обновить лимит")
async def cmd_refresh(message: Message):
    status = await generate_status_message(message.from_user.id)
    await message.answer(status, parse_mode="html")

@router.message(F.text == "❌ отмена")
async def cmd_cancel(message: Message, state: FSMContext):
    await state.clear()
    await message.answer("отменено", reply_markup=kb.get_main_keyboard())
