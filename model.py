import datetime
import redis
import json
from copy import copy
from dataclasses import dataclass

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

server = redis.Redis("localhost",6379,0)


# class Household_redis_adapter:
#     server = redis.Redis("localhost",6379,0)
    
#     def update(self):
#         self.server.set(self.key,pickle.dumps(self))

#     def __getitem__(self,key) :
#         return pickle.loads( self.server.get("key"))
    
#     def delete (self):
#         self.server.delete(self.key)

@dataclass
class Household_Response:
    status:bool
    msg:str
    data:object

class Household():

    def Redis_sync(func):
        def wrapper(self,*args,**kwargs):
            resp:Household_Response = func(self,*args,**kwargs)
            if resp.status:
                server.set(self.key,self.toJson())
            return resp
        return wrapper

    def __init__(self,key,name) -> None:
        self.name=name
        self.key = key
        self.budget = {}

        self.balance = {}
        self.balance_prev=[]

        self.sheet = []
        self.prev_sheets = []

    def toJson(self):
        return json.dumps(self, default=lambda o: o.__dict__, sort_keys=True, indent=4)

    def loadJson(self,valueSerialized):
        map(lambda key,value: self.__setattr__(key,value),valueSerialized)

    def get_balance_str(self):
        resp="Your household current balance is:\n\n"
        for name,value in self.balance.items():
            resp+=f"{name}: ${value}\n"
        
        resp += "----------------------"
        return Household_Response(True,"",resp)
    
    def get_budget_str(self):
        resp="Your household budget is:\n\n"
        for name,value in self.budget.items():
            resp+=f"{name}: ${value}\n"
        
        resp += "----------------------"
        return Household_Response(True,"",resp)

    @Redis_sync
    def add_budget(self,name,cap):
        if name not in self.budget:
            self.budget[name]= int(cap)
            self.balance[name] = int(cap)
            return Household_Response(True,"budget is added",None)
        else:
            return Household_Response(False,"budget already exist",None)

    @Redis_sync
    def remove_budget(self,name):
        if name not in self.budget:
            return Household_Response( False, "budget does not exist",None)
        else:
            del self.budget[name]
            del self.balance[name]
            return Household_Response( True,"budget got deleted successfully",None)

    @Redis_sync
    def reset_budget(self):
        self.balance = copy(self.budget)
        return Household_Response( True,"budget got restarted",None)

    @Redis_sync
    def add_cost(self,name,cost:int,user=None,date=None,text=None):
        if name in self.budget:
            self.sheet.append( Cost(cost,name,text,date,user))
            self.balance[name]-=cost
            self.update()
            return Household_Response(  True, "cost is registred",None)
        else:
            return Household_Response( False, "budget does not exist",None)

    def get_budget_categories(self):
        return Household_Response( True, "",self.budget.keys())
    
    @Redis_sync
    def finish_cycle(self):
        self.balance_prev.append((datetime.datetime.now(),copy(self.balance)))
        self.balance = copy(self.budget)
        return Household_Response( True, "Cycle is finsihed",None)
    
    def get_costs(self,page=0):
        resp = []
        # 10 options
        for i in range(10*page,10*page+1):
            resp.append((i, str(self.sheet[i])))

        return Household_Response( True, "",resp)
    
    @Redis_sync
    def remove_costs(self,i):
        try:
            cost:Cost = self.sheet[i]
            self.balance[cost.category] += cost.value # revet back the cost 
            del self.sheet[i]
            return Household_Response( True, "",None)
        except:
            return Household_Response( False, "",None)

    

