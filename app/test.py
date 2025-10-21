
import gspread
from google.oauth2.service_account import Credentials

SCOPES = ["https://www.googleapis.com/auth/spreadsheets",
          "https://www.googleapis.com/auth/drive"]

creds = Credentials.from_service_account_file("app/hungry-logs-bot-credential.json", scopes=SCOPES)
client = gspread.authorize(creds)

for ss in client.list_spreadsheet_files():
    print(ss)
