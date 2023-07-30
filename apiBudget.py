import enum
from typing import Any
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardMarkup, ReplyKeyboardRemove, Update, InlineQueryResultArticle, InputTextMessageContent
from telegram.ext import CommandHandler,MessageHandler,Filters,InlineQueryHandler,Updater,CallbackContext,ConversationHandler,CallbackQueryHandler
import logging
from copy import copy
import datetime
import redis

ACCOUNT_QUESTION=-1
ACCOUNT_NAME=0
ACCOUNT_CONTINUE=1
BUDGET_CATEGORY=range(1)
COST_OPTIONS,COST_SUBMIT=range(2)
households = {}
 


logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',level=logging.INFO)

class Cost:
    def __init__(self,value,category, text=None ,date=None,owner=None) -> None:
        self.value = value
        self.category = category
        if date is None:
            date = datetime.datetime.utcnow()
        self.date = date

        if owner is None:
            owner = "N/A"
        self.owner = owner

        if text is None:
            text = ""
        self.text = text

    def __str__(self) -> str:
        return f"{self.date}: ${self.value} - {self.text} by {self.owner}"

class Household:
    def __init__(self,name) -> None:
        self.name=name
        self.budget = {}

        self.balance = {}
        self.balance_prev=[]

        self.sheet = []
        self.prev_sheets = []


    def get_balance_str(self):
        resp="Your household current balance is:\n\n"
        for name,value in self.balance.items():
            resp+=f"{name}: ${value}\n"
        
        resp += "----------------------"
        return resp
    
    def get_budget_str(self):
        resp="Your household budget is:\n\n"
        for name,value in self.budget.items():
            resp+=f"{name}: ${value}\n"
        
        resp += "----------------------"
        return resp

    def add_budget(self,name,cap):
        if name not in self.budget:
            self.budget[name]= int(cap)
            self.balance[name] = int(cap)
            return True, "budget is added"
        else:
            return False,"budget already exist"

    def remove_budget(self,name):
        if name not in self.budget:
            return False, "budget does not exist"
        else:
            del self.budget[name]
            del self.balance[name]
            return True,"budget got deleted successfully"

    def reset_budget(self):
        self.balance = copy(self.budget)

    def add_cost(self,name,cost:int,user=None,date=None,text=None):
        if name in self.budget:
            self.sheet.append( Cost(cost,name,text,date,user))
            self.balance[name]-=cost
            return True, "cost is registred"
        else:
            return False, "budget does not exist"
        
    def get_budget_categories(self):
        return self.budget.keys()
    
    def finish_cycle(self):
        self.balance_prev.append((datetime.datetime.now(),copy(self.balance)))
        self.balance = copy(self.budget)

    def get_costs(self,page=0):
        resp = []
        # 10 options
        for i in range(10*page,10*page+1):
            resp.append((i, str(self.sheet[i])))

        return resp
    
    def remove_costs(self,i):
        try:
            cost:Cost = self.sheet[i]
            self.balance[cost.category] += cost.value # revet back the cost 
            del self.sheet[i]
            return True
        except:
            return False


class Household_redis_adapter:
    def __init__(self) -> None:
        self.server  = redis.Redis("localhost",6379,0)
    
    def __setitem__(self, key:str, value:Household):
        print (key)

    def __getitem__(self,key):
        pass
    

s= Household_redis_adapter()
s[0] = 12


with open("token.key","r") as file: 
    TOKEN = file.read()

updater = Updater(token=TOKEN, use_context=True)
dispatcher = updater.dispatcher

def balance(update: Update, context: CallbackContext):

    household = update.effective_chat.id
    user = update.effective_chat.username
    if household in households:
        context.bot.send_message(chat_id=update.effective_chat.id, text=households[household].get_balance_str())
    else:
        context.bot.send_message(chat_id=update.effective_chat.id, text="You should first start a household. Try /start.")

    # context.bot.send_message(chat_id=update.effective_chat.id, text="This should be associtaed ")

    # if  update.effective_chat.type == "group":
    #     householdID= update.effective_chat.id
    #     userID =  update.effective_chat.username
    #     if householdID not in households:
    #         context.bot.send_message(chat_id=update.effective_chat.id, text="You should first start a household.")
    #     else:
    #         users= households[householdID][1]

    #         context.bot.send_message(chat_id=update.effective_chat.id, text="Helloo")
    #         # for user_ in users:
    #         #     context.bot.send_message(chat_id=user_chatID_map[user_], text="User {}  requested for a polling session for household {}!".format(currentUser,households[householdID][0]))

    #         # if user in households[householdID][1]:
    #         #     context.bot.send_message(chat_id=update.effective_chat.id, text="User {} is already added to this household!".format(user))
    #         # else:
    #         #     if user not in users: 
    #         #         context.bot.send_message(chat_id=update.effective_chat.id, text="You need to register first in @HouseholdTreasurerBot")
    #         #     else:
    #         #         households[householdID].add(user)
    #         #         context.bot.send_message(chat_id=update.effective_chat.id, text="User {} is added to this household.".format(user))
    # else:
    #     context.bot.send_message(chat_id=update.effective_chat.id, text="This should be associtaed ")

def register(update: Update, context: CallbackContext):

    household = update.effective_chat.id
    user = update.effective_chat.username
    if household in households:
        context.bot.send_message(chat_id=update.effective_chat.id, text=f"This chat thread has been registered as household {households[household].name}")
    elif len(context.args) ==0:
        context.bot.send_message(chat_id=update.effective_chat.id, text="register your household based on following format:\n /register <household_name> ")
    else:
        name= " ".join(context.args)
        households[household]=Household(name)
        context.bot.send_message(chat_id=update.effective_chat.id, text=f"household {name} got registered")

def addBudget(update: Update, context: CallbackContext):

    household = update.effective_chat.id
    user = update.effective_chat.username
    if household not in households:
        context.bot.send_message(chat_id=update.effective_chat.id, text="Household doesn't exit. Register it first using the following command:\n /register <household_name> ")
    elif len(context.args) ==0:
        context.bot.send_message(chat_id=update.effective_chat.id, text="Add budget to your household based on following format:\n /add <budget_name> <budget_value> ")
    elif len(context.args) ==2:
        budget_name = context.args[0]
        budget_value = context.args[1]
        households[household].add_budget(budget_name,budget_value)
        context.bot.send_message(chat_id=update.effective_chat.id, text=f"budget {budget_name} with cap of ${budget_value} got registered")
    else:
        context.bot.send_message(chat_id=update.effective_chat.id, text="Wrong fromat: Add budget to your household based on following format:\n /add <budget_name> <budget_value> ")

def showBudgets(update: Update, context: CallbackContext):

    household = update.effective_chat.id
    user = update.effective_chat.username
    if household not in households:
        context.bot.send_message(chat_id=update.effective_chat.id, text="Household doesn't exit. Register it first using the following command:\n /register <household_name> ")
    else:
        context.bot.send_message(chat_id=update.effective_chat.id, text=f"{households[household].get_budget_str()}")

def addCost_entry(update: Update, context: CallbackContext):
    household = update.effective_chat.id
    user = update.effective_chat.username
    buttons=[]
    if household not in households:
        update.message.reply_text('Household does not exist. You need to first register a household.')
        return ConversationHandler.END
    elif len(context.args) ==1:
        for name in households[household].get_budget_categories():
            buttons.append(InlineKeyboardButton(name, callback_data=name))
        markup = InlineKeyboardMarkup([buttons])
        context.user_data['value']= context.args[0]  
        update.message.reply_text('What is the category of the cost you are submiting?\nSend /cancel to cancel the cost.',reply_markup=markup)
        return  BUDGET_CATEGORY
    else:
        update.message.reply_text('Wrong format: Use /cost <value>')
        return ConversationHandler.END
    
def addCost(update: Update, context: CallbackContext):
    ''' The user's reply to the name prompt comes here  '''
    household = update.effective_chat.id
    user = update.effective_chat.username
    
    household_obj:Household
    household_obj = households[household]
    household_obj.add_cost(update.callback_query.data,int(context.user_data["value"]))
    context.bot.send_message(chat_id=update.effective_chat.id,text= f'cost is added.\n{household_obj.get_balance_str()}')
    # ends this particular conversation flow
    return ConversationHandler.END

def cancel(update: Update, context: CallbackContext):
    update.message.reply_text("the cost adding is cancelled")
    return ConversationHandler.END

def echo(update: Update, context: CallbackContext):
    return ConversationHandler.END

def finish (update: Update, context: CallbackContext):
    household = update.effective_chat.id
    user = update.effective_chat.username
    buttons=[]
    if household not in households:
        update.message.reply_text('Household does not exist. You need to first register a household.')
        context.bot.send_message(chat_id=update.effective_chat.id,text= f'Household does not exist. You need to first register a household.')

    else:
        households[household].finish_cycle()
        context.bot.send_message(chat_id=update.effective_chat.id,text= f'Cycle is finished.\n{households[household].get_balance_str()}')

def remove_budget_entry (update: Update, context: CallbackContext):
    household = update.effective_chat.id
    user = update.effective_chat.username
    buttons=[]
    if household not in households:
        update.message.reply_text('Household does not exist. You need to first register a household.')
        context.bot.send_message(chat_id=update.effective_chat.id,text= f'Household does not exist. You need to first register a household.')
        return ConversationHandler.END
    else:
        for name in households[household].get_budget_categories():
            buttons.append(InlineKeyboardButton(name, callback_data=name))
        markup = InlineKeyboardMarkup([buttons])
        context.user_data['value']= context.args[0]  
        update.message.reply_text('What is the category of the budget you want to delete?\nSend /cancel to cancel the cost.',reply_markup=markup)
        return  BUDGET_CATEGORY

def remove_budget (update: Update, context: CallbackContext):
    household = update.effective_chat.id
    user = update.effective_chat.username
    
    household_obj:Household
    household_obj = households[household]
    state,txt = household_obj.remove_budget(update.callback_query.data)
    context.bot.send_message(chat_id=update.effective_chat.id,text= f'{txt}')
    # ends this particular conversation flow
    return ConversationHandler.END

def remove_cost_entry  (update: Update, context: CallbackContext):
    household = update.effective_chat.id
    user = update.effective_chat.username
    buttons=[]
    if household not in households:
        update.message.reply_text('Household does not exist. You need to first register a household.')
        context.bot.send_message(chat_id=update.effective_chat.id,text= f'Household does not exist. You need to first register a household.')
        return ConversationHandler.END
    else:
        return  COST_OPTIONS

def remove_cost_show(update: Update, context: CallbackContext):
    household = update.effective_chat.id
    user = update.effective_chat.username
    buttons=[]

    if 'page' not in  context.user_data:
        context.user_data['page'] = 0

    for i,cost in  households[household].get_costs( context.user_data['page']):
        buttons.append(InlineKeyboardButton(str(cost), callback_data=i))

    markup = InlineKeyboardMarkup([[buttons],[InlineKeyboardButton("...", callback_data=-1)]])
    update.message.reply_text('Select the cost you want to remove or type /cancel to cancel the action.',reply_markup=markup)
    return  COST_SUBMIT

def remove_cost  (update: Update, context: CallbackContext):
    household = update.effective_chat.id
    user = update.effective_chat.username
    page = context.user_data['page'] 
    selected_button=  update.callback_query.data 
    if selected_button == -1: 
        context.user_data['page'] +=1
        return  COST_OPTIONS
    else:
        resp = households[household].remove_costs( update.callback_query.data )
        if resp:
            context.bot.send_message(chat_id=update.effective_chat.id,text= f'Cost got deleted.')
        else:
            context.bot.send_message(chat_id=update.effective_chat.id,text= f'Could not delete the cost.')
        return ConversationHandler.END






balance_handler = CommandHandler('balance', balance)
dispatcher.add_handler(balance_handler)

balance_handler = CommandHandler('register', register)
dispatcher.add_handler(balance_handler)

balance_handler = CommandHandler('add', addBudget)
dispatcher.add_handler(balance_handler)

balance_handler = CommandHandler('show', showBudgets)
dispatcher.add_handler(balance_handler)

balance_handler = CommandHandler('finish', finish)
dispatcher.add_handler(balance_handler)

addingAccount = ConversationHandler(
    entry_points=[CommandHandler('cost', addCost_entry)],
    states={
        BUDGET_CATEGORY:[CallbackQueryHandler(addCost)]
    },
    fallbacks=[CommandHandler('cancel', cancel)],
    per_chat=True,
    
)
dispatcher.add_handler(addingAccount)

addingAccount = ConversationHandler(
    entry_points=[CommandHandler('remove', remove_budget_entry)],
    states={
        BUDGET_CATEGORY:[CallbackQueryHandler(addCost)]
    },
    fallbacks=[CommandHandler('cancel', cancel)],
    per_chat=True,
    
)
dispatcher.add_handler(addingAccount)


addingAccount = ConversationHandler(
    entry_points=[CommandHandler('del', remove_cost_entry)],
    states={
        COST_OPTIONS:[CallbackQueryHandler(remove_cost_show)],
        COST_SUBMIT:[CallbackQueryHandler(remove_cost)]

    },
    fallbacks=[CommandHandler('cancel', cancel)],
    per_chat=True,
    
)
dispatcher.add_handler(addingAccount)



if __name__ =="__main__":
    updater.start_polling()



# ─── Keys To Register To Botfather ────────────────────────────────────────────
# register - register your account
# balance - show the current balance of the household
# add - add budget to the household
# show - show household budgets
# cost - register a cost
# households - show info about households you are registered in
# cancel - to cancel the conversation
# finish - finish the cycle
# remove - remove a budget
# del - delete a cost
