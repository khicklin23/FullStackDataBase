import mysql.connector
import requests 
from bs4 import BeautifulSoup as bs 
import pandas as pd 
import csv
from tkinter import messagebox
import tkinter.messagebox
import customtkinter
import datetime
import random


#Connect To Database

mydb = mysql.connector.connect(
host="localhost",
user="root",
password = "", 
database="stocks"
)

mycursor = mydb.cursor()






#Grab information for all 503 S&P 500 companies

url = "https://en.wikipedia.org/wiki/List_of_S%26P_500_companies#S&P_500_component_stocks"
response = requests.get(url)
html_content = response.content
soup = bs(html_content, 'html.parser')
table = soup.find('table', {'class': 'wikitable sortable'})
data = [] 
rows = table.find_all('tr')
for row in rows[1:]: 
    columns = row.find_all('td')
    columns = [column.text.strip() for column in columns]
    data.append(columns)
    

#Conver to dataframe and insert into .csv

columns = ["Symbol", "sName", "GICS Sector", "GICS Sub-Industry", "Headquarters", "IPO", "stockID", "Founded"]
df = pd.DataFrame(data, columns=columns)
df_sorted = df.sort_values(by="sName")
df.to_csv('wikipedia.csv', index=False)  


#Grab Price Of Specific Stock / Sector Given Ticker Symbol

def get_price(symbol):
    url = f'https://www.google.com/search?q=${symbol}+price'  
    html = requests.get(url)
    soup = bs(html.text, 'html.parser')
    price_element = soup.find('div', class_='BNeawe iBp4i AP7Wnd')
    
    if price_element:
        price = price_element.text
        price = price.split()
        return price
    else:
        return "Price not found"
    

#Initialization of database tables in MySql

def createTables(cursor):
    
    cursor.execute("""
            CREATE TABLE IF NOT EXISTS Stocks (
                symbol VARCHAR(10) PRIMARY KEY,
                sName VARCHAR(255),
                GICS_Sector VARCHAR(255),
                GICS_Sub_Industry VARCHAR(255),
                Headquarters VARCHAR(255),
                IPO DATE,
                stockID VARCHAR(20),
                Founded INT
            )
        """)
    cursor.execute("""
            CREATE TABLE IF NOT EXISTS Users (
                userID INT PRIMARY KEY,
                userName VARCHAR(16),
                password VARCHAR(16),
                amount FLOAT,
                buying_power FLOAT
            )
        """)

    cursor.execute("""
            CREATE TABLE IF NOT EXISTS transactions (
                transID INT PRIMARY KEY AUTO_INCREMENT,
                symbol VARCHAR(10),
                price FLOAT,
                shares INT,
                value FLOAT,
                sale VARCHAR(4),
                userID INT,
                datetime DATETIME,
                FOREIGN KEY (userID) REFERENCES Users(userID)
            )
        """)
    cursor.execute("""
            CREATE TABLE IF NOT EXISTS positions (
                posID INT NOT NULL AUTO_INCREMENT,
                symbol VARCHAR(4) NULL,
                POS FLOAT,
                shares INT NULL,
                userID INT,  
                PRIMARY KEY (posID),
                FOREIGN KEY (userID) REFERENCES Users (userID)
            )
        """)
    
#createTables(mycursor

#Insert data from .csv into the MySql Database

def insert_data_from_csv(mydb, filename):
    cursor = mydb.cursor()
    try:
        with open(filename, 'r') as csvfile:
            csvreader = csv.reader(csvfile)
            next(csvreader)  # Skip first 
            for row in csvreader:
                symbol, sName, gics_sector, gics_sub_industry, headquarters, IPO, stockID, founded = row
                
                founded = int(founded.split('(')[0].strip()[:4])
                sql = "INSERT INTO Stocks (Symbol, sName, GICS_Sector, GICS_Sub_Industry, Headquarters, IPO, stockID, Founded) VALUES (%s, %s, %s, %s, %s, %s, %s, %s)"
                val = (symbol, sName, gics_sector, gics_sub_industry, headquarters, IPO, stockID, founded)
                cursor.execute(sql, val)
            mydb.commit()
            print("Data inserted successfully.")
    except Exception as e:
        #Doesnt break the database if there is an error in inserting data
        print("Error inserting data:", e)
        mydb.rollback()
    finally:
        cursor.close()

filename = 'wikipedia.csv'
#insert_data_from_csv(mydb, filename)





#Function to view all stocks and information in stocks table

def viewStockTable():
    cursor = mydb.cursor()
    cursor.execute("SELECT * FROM Stocks")
    items = cursor.fetchall()
    if not items:
        print("No data found in the Stocks table.")
        return
    print("Stocks Table:")
    for row in items:
        print(row)
    cursor.close()



#Function to clear all database data (full wipe)

def clearUsers(cursor):
    cursor.execute("DELETE FROM positions")
    cursor.execute("DELETE FROM transactions")
    cursor.execute("DELETE FROM Users")
    mydb.commit()


#Sector Dictionary

sectorID = {
    'Industrials': 'XLI',
    'Technology': 'XLK',
    'Utilities': 'XLU',
    'Financials': 'XLF',
    'Health Care': 'XLV',
    'Materials': 'XLB',
    'Consumer Discretionary': 'XLY',
    'Real Estate': 'XLRE',
    'Consumer Staples': 'XLP',
    'Communication Services': 'XLC',
    'Energy': 'XLE'
}


#Checks data for all sectors

def checkSectors():
    sectorList=[]
    for sName, sID in sectorID.items():
        priceList = get_price(sID) #Recieves some arr ['123.53', '+1.25', '(0.86%)']"
        percent = float(priceList[2][1:-2]) #'(0.86%)' -> 0.86
        if priceList[1][0] != '+':
            percent *= -1  #If price change is negative then change percent too
        sectorList.append((sName, percent))

    finalList = sorted(sectorList, key=lambda x: x[1])

    return(finalList)
    





#Function for user initialization

def insertUser(cursor,userID,username,password):
    sql = "INSERT INTO Users (userID, userName, password, amount, buying_power) VALUES (%s, %s, %s, %s, %s)"
    val = (userID, username, password,0,25000)
    cursor.execute(sql, val)
    mydb.commit()


#Function for stock buy transaction + update posistions

def buyStock(cursor,symbol,userID,shares):
    price = get_price(symbol)
    value = float(price[0])
    total = round((value*shares),2)

    #Get current date and time
    time = datetime.datetime.now()

    #Format it to sql date and time format
    formatTime = time.strftime('%Y-%m-%d %H:%M:%S')

    #Check for existing position in the stock
    cursor.execute("SELECT shares, POS FROM positions WHERE symbol = %s AND userID = %s", (symbol, userID))
    existing_position = cursor.fetchone()

    if existing_position:
        #If there is an existing position update the share count and POS averaged
        existing_shares, existing_pos = existing_position
        new_shares = existing_shares + shares
        #Calculate the new average purchase POS price
        new_pos = ((existing_pos * existing_shares) + (value * shares)) / new_shares
        new_shares = existing_position[0] + shares
        cursor.execute("UPDATE positions SET shares = %s, POS = %s WHERE symbol = %s AND userID = %s", (new_shares, new_pos, symbol, userID))
    else:
        #Insert new position if there isnt a current one
        cursor.execute("INSERT INTO positions (symbol, POS, userID, shares) VALUES (%s, %s, %s, %s)", (symbol, value, userID, shares))
    
    #Add to transactions
    sql = "INSERT INTO transactions (symbol, price, userID, shares, value, sale, datetime) VALUES (%s, %s, %s, %s, %s, %s, %s)"
    val = (symbol, value, userID, shares, total, "BUY", formatTime)
    cursor.execute(sql, val)

    #Update buying power and market value
    sql = "UPDATE Users SET amount = amount + %s, buying_power = buying_power - %s WHERE userID = %s"
    cursor.execute(sql, (total, total, userID))
    
    mydb.commit()









def sellStock(cursor, symbol, userID, shares):
    try:
        #Get current date and time
        time = datetime.datetime.now()

        #Format it to sql standards
        formatTime = time.strftime('%Y-%m-%d %H:%M:%S')

        price = get_price(symbol)
        value = float(price[0])
        total = round((value * shares), 2)
        
        cursor.execute("SELECT shares, POS FROM positions WHERE symbol = %s AND userID = %s", (symbol, userID))
        existing_position = cursor.fetchone()
        
        if existing_position:
            existing_shares, existing_pos = existing_position
            new_shares = existing_shares + shares

            new_pos = ((existing_pos * existing_shares) + (value * shares)) / new_shares
            new_shares = existing_position[0] - shares
            cursor.execute("UPDATE positions SET shares = %s, POS = %s WHERE symbol = %s AND userID = %s", (new_shares, new_pos, symbol, userID))
        else:
            #Insert new position
            cursor.execute("INSERT INTO positions (symbol, POS, userID, shares) VALUES (%s, %s, %s, %s)", (symbol, value, userID, -shares))
        
        
        #Insert transaction
        sql = "INSERT INTO transactions (symbol, price, userID, shares, value, sale, datetime) VALUES (%s, %s, %s, %s, %s, %s, %s)"
        val = (symbol, value, userID, shares, total, "SELL", formatTime)
        cursor.execute(sql, val)
        
        # Update user's amount and buying_power
        sql = "UPDATE Users SET amount = amount - %s, buying_power = buying_power + %s WHERE userID = %s"
        cursor.execute(sql, (total, total, userID))
        
        mydb.commit()


    except mysql.connector.Error as e:
        if e.errno == 1644:  
            messagebox.showerror("Error", "You cannot sell more shares than owned!")
            app.stockCount=0
        else:
            print("Error occurred during sell transaction:", e)
        mydb.rollback()



"""
Examples of manual user insertion
insertUser(mycursor,70900,'user','root')
buyStock(mycursor,'aapl',70900,8)
buyStock(mycursor,'amzn',70900,1)
buyStock(mycursor,'msft',70900,7)
buyStock(mycursor,'tsla',70900,10)
insertUser(mycursor,15861,'userAdmin2','secretPassword')
buyStock(mycursor,'amd',15861,1)
buyStock(mycursor,'dg',15861,7)
buyStock(mycursor,'f',70900,5)
sellStock(mycursor,'aapl',70900,3)
buyStock(mycursor,'aapl',15861,6)
sellStock(mycursor,'aapl',15861,3)
"""

#Function to get total value of user account

def totalValue(cursor,userID):
    sql = "SELECT amount, buying_power FROM users WHERE userID = %s"
    cursor.execute(sql,(userID,))
    items = cursor.fetchall()
    if items:
        total = float(items[0][0]) + float(items[0][1])
        #Returns buying power + current posistions value
        return total
    else:
        print("Invalid userID")
        return None


#Function for checking user PnL stats and updating database information

def profitNLoss(cursor,userID):
    #Chart = posID, symbol, POS, shares, userID
    #Grabs format ROW = (214, 'aapl', 183.38, 8, 70900)
    sql = "SELECT * FROM positions WHERE userID = %s"
    cursor.execute(sql,(userID,))
    items = cursor.fetchall()
    newAccountAmount =0.00

    profitNLoss= []
    total=0
    for row in items:
        symbol = str(row[1])
        POS = float(row[2])
        shares = int(row[3])
        
        priceList = get_price(str(symbol))
        currentPrice = float(priceList[0])
        #Gets current stock price ^ 
        currTotal = (currentPrice*shares) #Current value of shares owned
        newAccountAmount += (currTotal)
    
        #Gets individual stock PnL
        stockPNL = round(currTotal-(POS*shares),2)
        
        #Gets stock percent from POS
        percent_change = round(((currentPrice - POS) / POS) * 100, 2)

        #Format Handling
        if stockPNL >= 0:
            profitNLoss.append(f"{symbol.upper()}:  $+{stockPNL}  ({percent_change}%)")
        else:
            profitNLoss.append(f"{symbol.upper()}:  ${stockPNL}  ({percent_change}%)")
            
        total+=stockPNL

    #Update user markt value
    sql = "UPDATE Users SET amount = %s WHERE userID = %s"
    cursor.execute(sql, (newAccountAmount, userID))
    mydb.commit()

    #Return per-position PnL and Total PnL
    return(profitNLoss,total)



"""
////////////////////////////////////////

Start Of GUI Code:

////////////////////////////////////////
"""



customtkinter.set_appearance_mode("System")
customtkinter.set_default_color_theme("dark-blue")  #Set Default Theme

#Class Initialization for GUI

class App(customtkinter.CTk):
    def __init__(self):
        super().__init__()
        
        #Config window
        self.title("Database Project - Paper Trading")
        self.geometry(f"{1300}x{650}")

        #Config grid layout (4x4)
        self.grid_columnconfigure(1, weight=1)
        self.grid_columnconfigure((2, 3), weight=0)
        self.grid_rowconfigure((0, 1, 2), weight=0)



        #Create sidebar frame

        self.sidebar_frame = customtkinter.CTkFrame(self, width=140, corner_radius=0)
        self.sidebar_frame.grid(row=0, column=0, rowspan=8, sticky="nsew")
        self.sidebar_frame.grid_rowconfigure(8, weight=1)

        self.logo_label = customtkinter.CTkLabel(self.sidebar_frame, text="BirdBox", font=customtkinter.CTkFont(size=20, weight="bold"))
        self.logo_label.grid(row=0, column=0, padx=20, pady=(20, 10))
        

        self.appearance_mode_optionemenu = customtkinter.CTkOptionMenu(self.sidebar_frame, values=["Light", "Dark", "System"], command=self.change_appearance_mode_event)
        self.appearance_mode_optionemenu.grid(row=8, column=0, padx=20, pady=25, sticky="s")



        #Create search box and enter button

        self.entry = customtkinter.CTkEntry(self, placeholder_text="Enter a Stock Ticker Symbol")
        self.entry.grid(row=3, column=1, columnspan=2, padx=(20, 0), pady=(20, 20), sticky="nsew")


        self.main_button_1 = customtkinter.CTkButton(master=self, fg_color="transparent", border_width=2, text_color=("gray10", "#DCE4EE"),text="Search", command=self.search_button_event)
        self.main_button_1.grid(row=3, column=3, padx=(20, 20), pady=(20, 20), sticky="nsew")


        #Create textbox for stock information

        self.textbox = customtkinter.CTkTextbox(self, width=250,font=customtkinter.CTkFont(size=20, weight="bold"))
        self.textbox.grid(row=0, column=1, padx=(20, 0), pady=(20, 0), sticky="nsew")



        #Create tabview for sector data and open position PnL

        self.tabview = customtkinter.CTkTabview(self, width=250)
        self.tabview.grid(row=0, column=2, padx=(20, 0), pady=(20, 0), sticky="nsew")
        self.tabview.add("All Sectors")
        self.tabview.add("Open P&L")
        self.tabview.tab("All Sectors").grid_columnconfigure(0, weight=1) 
        self.tabview.tab("Open P&L").grid_columnconfigure(0, weight=1)

        
        

        #Sector Update Grid

        self.sector_label_all = customtkinter.CTkLabel(self.tabview.tab("All Sectors"), text="Insert sectors here")
        self.sector_label_all.grid(row=0, column=0, padx=20, pady=20)

        #Initialize sector web scraping and set to variable
        Sector_Update = checkSectors()

        #Set label to current sector values
        
        myStr =''
        for i, (sector, percent) in enumerate(Sector_Update):
            if float(percent) >= 0:
                # Make the positive percent sectors green
                if i == 0:
                    myStr += f"{sector}: {percent}%" + "   "
                    self.sector_label_all.configure(text=myStr, font=customtkinter.CTkFont(size=13, weight="bold"))
                else:
                    myStr += f"\n{sector}: {percent}%" + "   "
                    self.sector_label_all.configure(text=myStr, font=customtkinter.CTkFont(size=13, weight="bold"))
            else:
                if i ==0:
                    myStr += f"{sector}: {percent}%" + "   "
                    
                    self.sector_label_all.configure(text=myStr, font=customtkinter.CTkFont(size=13, weight="bold"))
                else:    
                    myStr += f"\n{sector}: {percent}%" + "   "
                    self.sector_label_all.configure(text=myStr, font=customtkinter.CTkFont(size=13, weight="bold"))

        #Use previous variable for text entry of Sector status's
        self.sector_label_all.configure(text=f"{myStr}")

        self.open_PnL_Label = customtkinter.CTkLabel(self.tabview.tab("Open P&L"), text="Login To View Your Open P&L")
        self.open_PnL_Label.grid(row=0, column=0, padx=20, pady=20)


        #Login Buttons Frame
        
        self.login = False
        
        self.login_frame = customtkinter.CTkScrollableFrame(self, label_text= "Login / Sign Up")
        self.login_frame.grid(row=0, column=3, padx=(20, 20), pady=(20, 0), sticky="nsew")


        #Login Button

        self.login_prompt_button = customtkinter.CTkButton(master=self.login_frame, text="Click To Login",command=self.login_button_click)
        self.login_prompt_button.grid(row=3, column=2, pady=10,padx=30, sticky="n")
        self.signUp_prompt_button = customtkinter.CTkButton(master=self.login_frame, text="Create An Account",command=self.signUp_button_click)
        self.signUp_prompt_button.grid(row=4, column=2, pady=10,padx=30, sticky="n")



        #Account P&L (Open and Life Time)
        
        self.profit_and_loss_frame = customtkinter.CTkTabview(self)
        self.profit_and_loss_frame.add("Open P&L")
        self.profit_and_loss_frame.add("Life Time Account P&L")
        self.profit_and_loss_frame.tab("Life Time Account P&L").grid_columnconfigure(0, weight=1) 
        self.profit_and_loss_frame.tab("Open P&L").grid_columnconfigure(0, weight=1)

        self.profit_and_loss_frame.grid(row=1, column=1, padx=(20, 0), pady=(20, 0), sticky="nsew")
        self.profit_and_loss_frame.grid_columnconfigure(0, weight=1)
        self.profit_and_loss_frame.grid_rowconfigure(4, weight=1)

        self.accountPNL_open = customtkinter.CTkLabel(self.profit_and_loss_frame.tab("Open P&L"), text="Login To View Your Account Info")
        self.accountPNL_open.grid(row=0, column=0, padx=20, pady=20)
        self.accountPNL_life = customtkinter.CTkLabel(self.profit_and_loss_frame.tab("Life Time Account P&L"), text="Login To View Your Account Info")
        self.accountPNL_life.grid(row=0, column=0, padx=20, pady=20)
        
        


        #Account Info
        self.scrollable_frame = customtkinter.CTkScrollableFrame(self, label_text="Account Information", width = 50)
        self.scrollable_frame.grid(row=1, column=2, padx=(20, 0), pady=(20, 0), sticky="nsew")
        self.scrollable_frame.grid_columnconfigure(0, weight=1)
        self.scrollable_frame.grid_rowconfigure(0, weight=1)

        self.user_total_label = customtkinter.CTkLabel(master=self.scrollable_frame, text = "Login To View Account Info",font=customtkinter.CTkFont(size=13, weight="bold"))
        self.user_total_label.grid(row=1, column=2, padx=(20, 80), pady=(20, 0), sticky="nsew")

        self.user_position_label = customtkinter.CTkLabel(master=self.scrollable_frame,text = "",font=customtkinter.CTkFont(size=13, weight="bold"))
        self.user_position_label.grid(row=2, column=2, padx=(20, 60), pady=(20, 0), sticky="nsew")

        self.user_buyingP_label = customtkinter.CTkLabel(master=self.scrollable_frame,text = "",font=customtkinter.CTkFont(size=13, weight="bold"))
        self.user_buyingP_label.grid(row=3, column=2, padx=(20, 60), pady=(20, 0), sticky="nsew")


        # Positions Box

        self.position_frame = customtkinter.CTkScrollableFrame(self, label_text = "My Positions")
        self.position_frame.grid(row=1, column=3, padx=(20, 20), pady=(20, 0), sticky="nsew")
        self.positions_label = customtkinter.CTkLabel(master=self.position_frame, text="Login to View Your Positions",font=customtkinter.CTkFont(size=12, weight="normal"))
        self.positions_label.grid(row=0, column=0, padx=(0,150), pady=20)

        #Default Stock Info status + Default Appearence Mode
        self.appearance_mode_optionemenu.set("Dark")
        self.textbox.insert("0.0", "Stock Info:\n\n" + "Search a stock in the search bar below to find out its information!")

    
        """
        ////////////////////////////////////
        End of Default Window Initialization
        ////////////////////////////////////
        """



    #Function to handle input from the search bar and retrieve stock data
    
    def search_button_event(self): 
        # Retrieve the text entered in the entry widget
        search_text = self.entry.get()
        cursor = mydb.cursor()
        cursor.execute("SELECT * FROM Stocks WHERE symbol = %s", (search_text,))
        items = cursor.fetchall()
        
        self.textbox.delete("1.0", "end")
        self.ticker_symbol = search_text
        
        #Use bot to scrape the live stock data
        currPrice = get_price(self.ticker_symbol)
        self.searchPrice = currPrice[0]
        
        if not items:
            #If the stock isnt in the stocks database, still insert symbol and live price
            self.textbox.insert("0.0",f"({self.ticker_symbol.upper()}): Price: ${currPrice[0]}\n\nThis Stock Is Not In The S&P 500.")
            
        else:    
            for row in items:
                #Code for displaying the stock data in the stock information textbox
                self.ticker_symbol = row[0]
                company_name = row[1]
                sector = row[2]
                industry = row[3]
                location = row[4]
                sp500 = row[5]
                cik = row[6]
                founded_year = row[7]
                #Constructing / Formatting the stock explanation
                explanation = f"({self.ticker_symbol.upper()}): Price: ${currPrice[0]}\n\n{company_name}  is a {industry} company in the {sector} sector."
                explanation += f" It was founded in {founded_year} in {location}."
                explanation += f" The Central Index Key for {company_name} is {cik}, It was initially added to the S&P 500 in {sp500}.\n\n"
                
            self.textbox.insert("0.0", explanation)

        #Function is ran if the user is logged in as an account
        if self.login:
            
            #Buy and sell button format
            self.sidebar_button_1 = customtkinter.CTkButton(self.sidebar_frame, text="Buy", command=self.buy_button_event, bg_color='transparent', fg_color='green')
            self.sidebar_button_1.grid(row=1, column=0, padx=20, pady=10, sticky="ew")
            self.sidebar_button_2 = customtkinter.CTkButton(self.sidebar_frame, text="Sell", command=self.sell_button_event, bg_color='transparent', fg_color='red')
            self.sidebar_button_2.grid(row=2, column=0, padx=20, pady=10, sticky="ew")

            # Plus and Minus Button format
            self.button_plus = customtkinter.CTkButton(self.sidebar_frame, text="+", command=self.plus_button_event, bg_color='transparent', fg_color='blue')
            self.button_plus.grid(row=3, column=0, padx=20, pady=15, sticky="ew")
            self.button_minus = customtkinter.CTkButton(self.sidebar_frame, text="-", command=self.minus_button_event, bg_color='transparent', fg_color='grey')
            self.button_minus.grid(row=4, column=0, padx=20, pady=15, sticky="ew")
            self.stockCount = 0
            self.label_number = customtkinter.CTkLabel(self.sidebar_frame, text=f"Shares: {self.stockCount}", font=customtkinter.CTkFont(size=14, weight="bold"))
            self.label_number.grid(row=5, column=0, padx=20, pady=5, sticky="ew")

            #Format for labels under side pannel buttons
            self.MarketValue = 0
            self.value_number = customtkinter.CTkLabel(self.sidebar_frame, text=f"Market Value: ${self.MarketValue}", font=customtkinter.CTkFont(size=14, weight="bold"))
            self.value_number.grid(row=6, column=0, padx=20, pady=5, sticky="ew")

            self.buyingP_left_number = customtkinter.CTkLabel(self.sidebar_frame, text=f"Buying Power: ${round(float(self.buyingP),2)}", font=customtkinter.CTkFont(size=14, weight="bold"))
            self.buyingP_left_number.grid(row=7, column=0, padx=20, pady=0, sticky="ew")
            
        cursor.close()
        
            





    #Function for logging in
    
    def login_button_click(self):
        #Initialize window
        dialog = customtkinter.CTkInputDialog(text="Username:", title="Login Window")
        username = dialog.get_input()
        dialog = customtkinter.CTkInputDialog(text="Password:", title="Login Window")
        password = dialog.get_input()

        #Check database for inputed username and password
        mycursor.execute("SELECT userID FROM users WHERE userName = %s AND password = %s", (username,password))
        id = str(mycursor.fetchone())

        #id is set to none if the user is not in the database
        if id != "None":
            self.user_ID = int(id[1:-2]) #Remove sql formating and convert back to int
            self.login = True #Let the class know that the user is now logged in!
            
            self.login_frame.configure(label_text = f"Welcome {username}")
            self.login_prompt_button.configure(text="Login As Another User")
            #Updating position numbers and all data labels
            self.update_positions()
            
        else:
            #Pop up window if the credentials are invalid / non existent 
            messagebox.showerror("Error", "Invalid Credentials.")
            

    #Function for creating a new user account
    def signUp_button_click(self):
        # Get username and password from user input dialogs
        dialog = customtkinter.CTkInputDialog(text="Create a Username:", title="Sign Up Window")
        username = dialog.get_input()
        dialog = customtkinter.CTkInputDialog(text="Enter a Password:", title="Sign Up Window")
        password = dialog.get_input()
        #Check if username already exists
        mycursor.execute("SELECT * FROM Users WHERE userName = %s", (username,))
        existing_user = mycursor.fetchone()

        #Make sure the username does not already exists
        if existing_user:
            messagebox.showerror("Error", "username already exists.")
            return
        userID = random.randint(10000, 99999)
        insertUser(mycursor,userID,str(username),str(password))

        #Automatically prompt for login after successfull login
        self.login_button_click()
                        

    #Function to update all stock and database data
    def update_positions(self):
        #Recieve per-position PnL and Overall PnL
        positionPnL, total_open_PnL = profitNLoss(mycursor,self.user_ID)

        #Update text for all individual position updates
        text=''
        for item in positionPnL:
            text += f"{item}\n\n"
        self.open_PnL_Label.configure(text = f"{text}")

        #Set label for total account value
        totAccWorth = totalValue(mycursor,self.user_ID)
        totAccWorth = "{:.2f}".format(round(totAccWorth,2))
        self.user_total_label.configure(text = f"Account Value: ${totAccWorth}")

        #Grab updated amount (After running profitNLoss() ) and set to label
        mycursor.execute("SELECT amount from users WHERE userID = %s", (self.user_ID,))
        amount = str(mycursor.fetchone())
        amount = str(amount[1:-2])
        val = round(float(amount),2)
        val = "{:.2f}".format(val)
        self.user_position_label.configure(text = f"Market Value: ${val}")

        #Update buying power as well
        mycursor.execute("SELECT buying_power from users WHERE userID = %s", (self.user_ID,))
        self.buyingP = str(mycursor.fetchone())
        self.buyingP = str(self.buyingP[1:-2])
        val = round(float(self.buyingP),2)
        val = "{:.2f}".format(val)
        self.user_buyingP_label.configure(text = f"Buying Power: ${val}")

        #Format and label updating for acive position information
        sql = ("SELECT * FROM positions WHERE userID = %s")
        mycursor.execute(sql,(self.user_ID,))
        items = mycursor.fetchall()
        
        #Check and see if there are active positions
        if not items:
            self.positions_label.configure(text=f"No Active Positions")
            return
            
        #Format of items[] = (214, 'aapl', 183.38, 8, 70900)
        positions= ''
        
        for row in items:
            symbol = str(row[1])
            unRoundPOS = round(float(row[2]),2)
            POS = "{:.2f}".format(unRoundPOS)
            positions += f"{symbol.upper()}:  {row[3]} Shares @ POS ${POS}\n\n"
            
        #Set for position data share count and updated POS
        self.positions_label.configure(text=f"{positions}")

        #Get life time account PnL and set to label
        acctPNL = round(float(totAccWorth)-25000,2)
        
        if acctPNL>=0:
            acctPNL = "{:.2f}".format(acctPNL)
            self.accountPNL_life.configure(text=f"\n\n Life Time P&L = $+{acctPNL}", text_color="green", font=customtkinter.CTkFont(size=16, weight="bold"))
        else:
            acctPNL = "{:.2f}".format(acctPNL)
            self.accountPNL_life.configure(text=f"\n\n Life Time P&L = ${acctPNL}", text_color="red", font=customtkinter.CTkFont(size=16, weight="bold"))

        #Get current total open PnL and set to label
        if total_open_PnL>=0:
            total_open_PnL = "{:.2f}".format(total_open_PnL)
            self.accountPNL_open.configure(text=f"\n\n Open P&L = $+{total_open_PnL}", text_color="green", font=customtkinter.CTkFont(size=16, weight="bold"))
        else:
            total_open_PnL = "{:.2f}".format(total_open_PnL)
            self.accountPNL_open.configure(text=f"\n\n Open P&L = ${total_open_PnL}", text_color="red", font=customtkinter.CTkFont(size=16, weight="bold"))


    
    #Stock count button plus click handling
    
    def plus_button_event(self):
        #Stock count variable for amount to buy / sell updated
        self.stockCount+=1
        #Grab buying power
        buyingPleft = float(self.buyingP)
        #Buying power left after purchasing given number of stocks
        buyingPleft = round((buyingPleft - (float(self.searchPrice) * self.stockCount)),2)

        #Prevent overbuying
        if buyingPleft < 0:
            self.stockCount-=1
            return #break
        #Format Buying Power Left Label
        buyingPleft = "{:.2f}".format(buyingPleft)
        self.buyingP_left_number.configure(text = f"Buying Power: ${round(float(buyingPleft),2)}")

        self.label_number.configure(text=f"Shares: {self.stockCount}")
        self.button_minus.configure(fg_color="blue")
        
        #Format market value label of searched stock symbol * number of shares being requested (total value)
        marketValue = round((float(self.searchPrice)*self.stockCount),2)
        marketValue = "{:.2f}".format(marketValue)
        self.value_number.configure(text=f"Market Value: ${marketValue}")


    
    #Stock count button minus click handling
    
    def minus_button_event(self):
        #Preventing negative sell count
        if self.stockCount >=1:
            if self.stockCount <= 1:
                self.button_minus.configure(fg_color="grey")
            else:
                self.button_minus.configure(fg_color="blue")

            self.stockCount-=1
            buyingPleft = float(self.buyingP)
            buyingPleft = round((buyingPleft - (float(self.searchPrice) * self.stockCount)),2)    
            if buyingPleft > 0:  
                buyingPleft = "{:.2f}".format(buyingPleft)
                self.buyingP_left_number.configure(text = f"Buying Power: ${buyingPleft}")
            marketValue = round((float(self.searchPrice)*self.stockCount),2)
            self.label_number.configure(text=f"Shares: {self.stockCount}")
            marketValue = "{:.2f}".format(marketValue)
            self.value_number.configure(text=f"Market Value: ${marketValue}")


    #Appearence mode button switch handling
    
    def change_appearance_mode_event(self, new_appearance_mode: str):
        customtkinter.set_appearance_mode(new_appearance_mode)


    #Buy button press handling
    
    def buy_button_event(self):
        buyingPleft = float(self.buyingP)
        buyingPleft = (buyingPleft - (float(self.searchPrice) * self.stockCount))
        #Double checking to make sure the user has proper funds if GUI fails
        if buyingPleft > 0:
            buyStock(mycursor,self.ticker_symbol,self.user_ID,self.stockCount)
            #Resetting Values then updating
            self.stockCount = 0
            self.label_number.configure(text=f"Shares: {self.stockCount}")
            self.update_positions()
        else:
            #Error Handling
            messagebox.showerror("Error", "Insufficient Funds.")
        

    #Sell button event handling
    
    def sell_button_event(self):
        sellStock(mycursor,self.ticker_symbol,self.user_ID,self.stockCount)
        self.stockCount = 0
        self.label_number.configure(text=f"Shares: {self.stockCount}")
        #SQL Trigger will prevent overselling of a stock

        #Updating all values
        self.update_positions()
    

#Launch App
if __name__ == "__main__":
    app = App()
    app.mainloop()
