import enum
import io
from typing import Any
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardMarkup, ReplyKeyboardRemove, Update, InlineQueryResultArticle, InputTextMessageContent
from telegram.ext import CommandHandler,MessageHandler,Filters,InlineQueryHandler,Updater,CallbackContext,ConversationHandler,CallbackQueryHandler
import logging
from model import *
import csv




ACCOUNT_QUESTION=-1
ACCOUNT_NAME=0
ACCOUNT_CONTINUE=1
BUDGET_CATEGORY=range(1)
COST_OPTIONS,COST_SUBMIT=range(2)
households = {}

def populateFromCache():
    households_ = Household.populate_multiple() 
    household:Household
    for household in households_:
        households[household.key]=household

logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',level=logging.INFO)


with open("token.key","r") as file: 
    TOKEN = file.read()

updater = Updater(token=TOKEN, use_context=True)
dispatcher = updater.dispatcher

def balance(update: Update, context: CallbackContext):

    household = str(update.effective_chat.id)
    user = update.effective_user.username
    if household in households:
        context.bot.send_message(chat_id=update.effective_chat.id, text=households[household].get_balance_str().data)
    else:
        context.bot.send_message(chat_id=update.effective_chat.id, text="You should first register a household. Try /register.")

def register(update: Update, context: CallbackContext):

    household = str(update.effective_chat.id)
    user = update.effective_user.username
    if household in households:
        context.bot.send_message(chat_id=update.effective_chat.id, text=f"This chat thread has been registered as household {households[household].name}")
    elif len(context.args) ==0:
        context.bot.send_message(chat_id=update.effective_chat.id, text="register your household based on following format:\n /register <household_name> ")
    else:
        name= " ".join(context.args)
        households[household]=Household.create(household,name)
        context.bot.send_message(chat_id=update.effective_chat.id, text=f"household {name} got registered")

def addBudget(update: Update, context: CallbackContext):

    household = str(update.effective_chat.id)
    user = update.effective_user.username
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

    household = str(update.effective_chat.id)
    user = update.effective_user.username
    if household not in households:
        context.bot.send_message(chat_id=update.effective_chat.id, text="Household doesn't exit. Register it first using the following command:\n /register <household_name> ")
    else:
        context.bot.send_message(chat_id=update.effective_chat.id, text=f"{households[household].get_budget_str().data}")

def addCost_entry(update: Update, context: CallbackContext):
    household = str(update.effective_chat.id)
    user = update.effective_user.username
    buttons=[]
    if household not in households:
        update.message.reply_text('Household does not exist. You need to first register a household.')
        context.user_data.clear()
        return ConversationHandler.END
    elif len(context.args) >=1:
        for name in households[household].get_budget_categories().data:
            buttons.append(InlineKeyboardButton(name, callback_data=name))
        markup = InlineKeyboardMarkup([buttons])
        context.user_data['value']= context.args[0]  
        context.user_data['text'] =None
        if len(context.args) >=2:
            context.user_data['text'] = ' '.join(context.args[1:]  )
        update.message.reply_text('What is the category of the cost you are submiting?\nSend /cancel to cancel the cost.',reply_markup=markup)
        return  BUDGET_CATEGORY
    else:
        update.message.reply_text('Wrong format: Use /cost <value> <txt optional>')
        context.user_data.clear()
        return ConversationHandler.END
    
def addCost(update: Update, context: CallbackContext):
    ''' The user's reply to the name prompt comes here  '''
    household = str(update.effective_chat.id)
    user = update.effective_user.username
    
    household_obj:Household
    household_obj = households[household]
    household_obj.add_cost(update.callback_query.data,float(context.user_data["value"]),user,text=context.user_data['text'])
    context.bot.send_message(chat_id=update.effective_chat.id,text= f'cost is added.\n{household_obj.get_balance_str().data}')
    # ends this particular conversation flow
    context.user_data.clear()
    return ConversationHandler.END

def cancel(update: Update, context: CallbackContext):
    update.message.reply_text("the conversation is cancelled")
    context.user_data.clear()
    return ConversationHandler.END

def echo(update: Update, context: CallbackContext):
    context.user_data.clear()
    return ConversationHandler.END

def finish (update: Update, context: CallbackContext):
    household = str(update.effective_chat.id)
    user = update.effective_user.username
    buttons=[]
    if household not in households:
        update.message.reply_text('Household does not exist. You need to first register a household.')
        context.bot.send_message(chat_id=update.effective_chat.id,text= f'Household does not exist. You need to first register a household.')

    else:
        if households[household].finish_cycle().status:
            context.bot.send_message(chat_id=update.effective_chat.id,text= f'Cycle is finished.\n{households[household].get_balance_str().data}')
        else:
            context.bot.send_message(chat_id=update.effective_chat.id,text= 'something went wrong!')

def remove_budget_entry (update: Update, context: CallbackContext):
    household = str(update.effective_chat.id)
    user = update.effective_user.username
    buttons=[]
    if household not in households:
        update.message.reply_text('Household does not exist. You need to first register a household.')
        context.bot.send_message(chat_id=update.effective_chat.id,text= f'Household does not exist. You need to first register a household.')
        context.user_data.clear()
        return ConversationHandler.END
    else:
        for name in households[household].get_budget_categories().data:
            buttons.append(InlineKeyboardButton(name, callback_data=name))
        markup = InlineKeyboardMarkup([buttons])
        context.user_data['value']= context.args[0]  
        update.message.reply_text('What is the category of the budget you want to delete?\nSend /cancel to cancel the cost.',reply_markup=markup)
        return  BUDGET_CATEGORY

def remove_budget (update: Update, context: CallbackContext):
    household = str(update.effective_chat.id)
    user = update.effective_user.username
    
    household_obj:Household
    household_obj = households[household]
    resp= household_obj.remove_budget(update.callback_query.data)
    context.bot.send_message(chat_id=update.effective_chat.id,text= f'{resp.msg}')
    # ends this particular conversation flow
    context.user_data.clear()
    return ConversationHandler.END

def remove_cost_entry  (update: Update, context: CallbackContext):
    household = str(update.effective_chat.id)
    user = update.effective_user.username
    buttons=[]
    if household not in households:
        update.message.reply_text('Household does not exist. You need to first register a household.')
        context.bot.send_message(chat_id=update.effective_chat.id,text= f'Household does not exist. You need to first register a household.')
        context.user_data.clear()
        return ConversationHandler.END
    else:

        return  remove_cost_show(update,context)

def remove_cost_show(update: Update, context: CallbackContext,more=False):
    household = str(update.effective_chat.id)
    user = update.effective_user.username
    buttons=[]

    if 'page' not in  context.user_data:
        context.user_data['page'] = 0

    for i,cost in  households[household].get_costs( context.user_data['page']).data:
        buttons.append([InlineKeyboardButton(str(cost), callback_data=i)])

    buttons.append([InlineKeyboardButton("...", callback_data='-1')])
    markup = InlineKeyboardMarkup(buttons)
    if more:
        context.bot.send_message(chat_id=update.effective_chat.id,text= f'Select the cost you want to remove or type /cancel to cancel the action.',reply_markup=markup)
    else:
        update.message.reply_text('Select the cost you want to remove or type /cancel to cancel the action.',reply_markup=markup)
    return  COST_SUBMIT

def remove_cost  (update: Update, context: CallbackContext):
    household = str(update.effective_chat.id)
    user = update.effective_user.username
    page = context.user_data['page'] 
    selected_button=  update.callback_query.data 
    if selected_button == '-1': 
        context.user_data['page'] +=1
        return  remove_cost_show(update,context,True)
    else:
        resp = households[household].remove_costs( int(update.callback_query.data ))
        if resp.status:
            context.bot.send_message(chat_id=update.effective_chat.id,text= f'Cost got deleted.')
        else:
            context.bot.send_message(chat_id=update.effective_chat.id,text= f'Could not delete the cost.')
        context.user_data.clear()
        return ConversationHandler.END

def report_cycle(update: Update, context: CallbackContext):
    household = str(update.effective_chat.id)
    user = update.effective_user.username
    buttons=[]
    if household not in households:
        update.message.reply_text('Household does not exist. You need to first register a household.')
        context.bot.send_message(chat_id=update.effective_chat.id,text= f'Household does not exist. You need to first register a household.')

    else:
        cost:Cost
        resp=""
        
        csv_buffer = io.StringIO()

        csv_writer = csv.DictWriter(csv_buffer,fieldnames=Cost.fields())
        csv_writer.writeheader()
        for i,cost in  households[household].get_costs(None).data:
            csv_writer.writerow(cost.__dict__)

        csv_data = csv_buffer.getvalue()
        csv_buffer.close()

        context.bot.send_document(chat_id=update.effective_chat.id, document=io.BytesIO(csv_data.encode()), filename='data.csv')


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

balance_handler = CommandHandler('report', report_cycle)
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
    populateFromCache()
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
# report - report the current cycle as a csv file
