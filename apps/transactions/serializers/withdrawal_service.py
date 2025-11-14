from intasend import APIService

# Replace with your actual IntaSend API key
token = ""

# Initialize IntaSend service
service = APIService(token=token, test=True)  # use test=False for production

# Define transactions
transactions = [
    {"name": "Awesome Customer", "account": "254745897362", "amount": 100},
]

# Set requires_approval to NO
response = service.transfer.mpesa(
    currency="KES",
    transactions=transactions,
    requires_approval="NO"
)

print("Withdrawal response:", response)
