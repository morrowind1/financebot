from aiogram.fsm.state import State, StatesGroup

class BudgetStates(StatesGroup):
    waiting_for_budget = State()
    waiting_for_payday = State()
    waiting_for_month = State()

class ExpenseStates(StatesGroup):
    waiting_for_description = State()
    waiting_for_amount = State()
    waiting_for_category = State()

class GoalStates(StatesGroup):
    waiting_for_title = State()
    waiting_for_target = State()
    waiting_for_deposit = State()
    waiting_for_withdraw = State()
