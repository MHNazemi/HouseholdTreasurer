import datetime
import json
from copy import copy, deepcopy
from dataclasses import dataclass
from dataAdapter import add_entity,get_all
import time
from datetime import datetime
class Cost:
    def __init__(self,value,category, text=None ,date=None,owner=None,budget=None) -> None:
        self.value = value
        self.category = category
        if date is None:
            date = time.time()
        self.date = date

        if owner is None:
            owner = "N/A"
        self.owner = owner

        if budget is None:
            budget = "N/A"
        self.budget = budget

        if text is None:
            text = ""
        self.text = text

    def __str__(self) -> str:
        return f"${self.value}: {datetime.strftime( datetime.fromtimestamp( self.date),'%d/%m/%Y, %H:%M') } on {self.budget}/{self.text}\n by {self.owner}"

    def populate(self,values:dict):
        for key,value in values.items():
            setattr(self,key,value)

    def csv(self):
        return f"{self.value},{datetime.strftime( datetime.fromtimestamp( self.date),'%d/%m/%Y, %H:%M') },{self.budget},{self.text},{self.owner}"
    
    @staticmethod
    def fields():
        return ["value","date","budget","text","owner","category" ]
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

    
    @staticmethod
    def populate_multiple():
        objs = get_all()
        resp = []
        for obj in objs:
            h = Household()
            h.populate(json.loads(obj))
            resp.append(h)
        return resp

    def Redis_sync(func):
        def wrapper(self,*args,**kwargs):
            resp:Household_Response = func(self,*args,**kwargs)
            if resp.status:
                add_entity(self.key,self.toJson())
            return resp
        return wrapper

    def __init__(self,key=None,name=None) -> None:
        self.name=name
        self.key = key
        self.budget = {}

        self.balance = {}
        self.balance_prevs=[]

        self.sheet = []
        self.sheet_prevs = []

        self.max_cycle=30
        self.max_sheet=500

    @staticmethod
    def create(key=None,name=None):
        household = Household(key,name)
        add_entity(str(household.key),household.toJson())
        return household

    def toJson(self):
        return json.dumps(self, default=lambda o: o.__dict__, sort_keys=True, indent=4)

    def populate(self,values:dict):
        for key,value in values.items():
            if key =='sheet':
                for value_ in value:
                    c= Cost(0,"")
                    c.populate(value_)
                    self.sheet.append(c)
            elif key =="sheet_prevs":
                for time_ , costs in value:
                    cycle = []
                    for cost in costs:
                        c= Cost(0,"")
                        c.populate(cost)
                        cycle.append(c)
                    self.sheet_prevs.append((time_,cycle))
            else:
                setattr(self,key,value)

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
            self.budget[name]= float(cap)
            self.balance[name] = float(cap)
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
    def add_cost(self,name,cost:float,user=None,date=None,text=None):
        if name in self.budget:
            if len(self.sheet)>self.max_sheet:
                self.sheet.pop(0) # remove the oldest one
                
            self.sheet.append( Cost(cost,name,text,date,user,name))
            self.balance[name]-=cost
            return Household_Response(  True, "cost is registred",None)
        else:
            return Household_Response( False, "budget does not exist",None)

    def get_budget_categories(self):
        return Household_Response( True, "",self.budget.keys())
    
    @Redis_sync
    def finish_cycle(self):
        finish_time = time.time()
        if len(self.balance_prevs)>self.max_cycle:
            self.balance_prevs.pop(0) # remove the oldest one
            self.sheet_prevs.pop(0) # remove the oldest one

        self.balance_prevs.append((finish_time,deepcopy(self.balance)))
        self.balance = copy(self.budget)

        self.sheet_prevs.append((finish_time,deepcopy(self.sheet)))
        self.sheet.clear()

        return Household_Response( True, "Cycle is finsihed",None)
    
    def get_costs(self,page=None):
        resp = []
        # 10 options
        if page is None:
            range_ = range(len(self.sheet)-1,-1,-1)
        else:
            range_ = range( max(-1, (len(self.sheet)-1) - (page*10) ) ,-1,-1)
        for i in range_:
            resp.append((i,self.sheet[i]))

        return Household_Response( True, "",resp)
    
    @Redis_sync
    def remove_costs(self,i:int):
        try:
            cost:Cost = self.sheet[i]
            self.balance[cost.category] += cost.value # revet back the cost 
            del self.sheet[i]
            return Household_Response( True, "",None)
        except:
            return Household_Response( False, "",None)

    

