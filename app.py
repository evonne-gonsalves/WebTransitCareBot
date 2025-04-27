from flask import Flask, render_template, request, jsonify
import numpy as np
from typing import Optional
from random import randint
from datetime import datetime
import json
from google import genai
import os  # Import os for environment variables

app = Flask(__name__)

# --- Electronic Store Bot Logic ---
menu_array = np.array([
    ['Mobile', 100],
    ['Charger', 20],
    ['Smart Watch', 50],
    ['Headphone', 30],
    ['Earbuds', 15],
    ['Power Bank', 25],
    ['USB Disk', 10]
])

order = []
placed_order = []
Event_log = []


def get_order() -> list[tuple[str, list[str]]]:
    """Returns the customer's order."""
    Event_log.append("Function Name: " + "get_order")
    return order


def remove_item(n: int) -> str:
    """Removes the nth (one-based) item from the order.

    Returns:
        The item that was removed.
    """
    Event_log.append("Function Name: " + "remove_item")
    Event_log.append("Agrument: " + f"{n}")

    try:
        item, _, _ = order.pop(n - 1)  # Assuming order contains (item, quantity, price)
        return item
    except IndexError:
        return f"Error: Item number {n} not found in order."


def clear_order() -> None:
    """Removes all items from the customer's order."""
    Event_log.append("Function Name: " + "clear_order")
    order.clear()


def place_order() -> int:
    """Submit the order to the kitchen.

    Returns:
        The estimated number of minutes until the order is ready.
    """
    global placed_order  # Access the global placed_order variable

    placed_order[:] = order.copy()
    Event_log.append("Function Name: " + "place_order")
    Event_log.append("Agrument: " + f"{placed_order} ")

    # Calculate total price
    total_price = sum(item[2] for item in placed_order)  # Access the total item price from the tuple

    print(json.dumps({'total_price': f'${total_price:.2f}'}))  # Corrected JSON key and formatted total price

    # Generate receipt
    receipt = f"""\n \n \n
    ==========================================
              Best Buy Receipt
    ==========================================
    Date: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}
    Address: 123 Main St, New York, NY 10001
    ------------------------------------------
    {'Item':<20}{'Quantity':<10}{'Price':<10}{'Total':<10}
    """
    for item, quantity, total_item_price in placed_order:
        # Get item cost from menu_array
        item_cost = 0  # Initialize item_cost to 0 before the inner loop
        for product in menu_array:
            if product[0] == item:
                item_cost = int(product[1])  # Ensure item_cost is an integer
                break  # Exit the inner loop after finding the item_cost
        receipt += f"{item:<20}{quantity:<10}${item_cost:<7.2f}${total_item_price:<7.2f}\n"  # Add item to receipt
    receipt += f"------------------------------------------\n"
    receipt += f"{'Total:':<30}${total_price:<7.2f}\n"  # Adjusted indentation
    receipt += f"------------------------------------------\n"
    receipt += f"     Thanks for shopping with us\n"
    receipt += f"------------------------------------------\n"

    print(receipt)  # Print the receipt

    clear_order()
    return total_price  # Return the total price


def exit_without_order() -> None:
    """Sets the exit_without_order flag to 1, indicating the customer wants to exit without ordering."""
    Event_log.append("Function Name: " + "exit_without_order")
    global exit_without_order
    exit_without_order = 1  # Set the flag


def exit_now() -> None:
    """Sets the exit_now flag to 1, indicating an immediate exit."""
    global exit_now
    exit_now = 1  # Set the flag


def confirm_order() -> str:
    """Asks the customer if the order is correct.

    Returns:
        The user's free-text response.
    """
    Event_log.append("Function Name: " + "confirm_order")
    print("Your order:")
    if not order:
        print("  (no items)")
        Event_log.append("Agrument: " + "No order ")

    for item, quantity, total_price in order:  # Changed to access quantity
        print(f"  {item} x {quantity} - ${total_price}")  # Display quantity and total price
        Event_log.append("Agrument: " + f"{item} x {quantity} - ${total_price} ")

    return input("Is this correct? ")


def add_to_order_price(item: str, quantity: int) -> None:
    """Adds the specified item to the customer's order, including quantity and price.

    Prints the cost of the added item in a JSON format for easy parsing.
    """
    Event_log.append("Function Name: " + "add_to_order_price")
    Event_log.append("Argument: " + f"{item} with quantity {quantity}")

    # Get item cost from menu_array
    item_cost = 0
    for product in menu_array:
        if product[0] == item:
            item_cost = int(product[1])  # Ensure item_cost is an integer
            break

    # Append (item, quantity, price) to order
    order.append((item, quantity, item_cost * quantity))  # Calculate item total price
    print(
        f"Added to order: {item} with quantity {quantity} @ unit rate ${item_cost} = total ${item_cost * quantity} ")

    # Print item cost as a JSON object
    # print(json.dumps({'item_cost': item_cost * quantity}))  # Print total item cost


def print_menu() -> None:
    """Prints the menu of available items."""
    Event_log.append("Function Name: " + "print_menu")
    print("\nProduct list:")
    print("Electronics:")
    for item, price in menu_array:
        # Convert price to a standard Python float before formatting
        print(f"{item:<20} - ${float(price):.2f}")
    print()  # Add a blank line after the menu

RETAIL_BOT_PROMPT_FEWSHOT = """

You are an online electronics store assistant. You will only respond with information about ordering items from the menu. Do not respond to any unrelated questions.

Your goal is to use the provided functions to take a complete order from the user, and then place the order.

You are restricted to talk only about items on the MENU. Do not talk about anything but ordering MENU items for the customer, ever.
At start of session welcome the customer, show him the MENU using the `print_menu` function and asked him to select the items he wants to order.
At start of session welcome the customer, show him the MENU using the `print_menu` function and asked him to select the items he wants to order.
Your goal is to do place_order after understanding the items and quantities the customer wants.
Always ask for quantity before adding to the order.

Add items to the customer's order with add_to_order_price, which will print like this: " Headphone with quantity 5 @ unit rate $30 = total $150""`. Parse this JSON object to get the item_price and show it to the customer like this : Okay, I've added 5 Mobiles to your order. The cost for 5 Mobiles is $500. Would you like to order anything else?



To see the contents of the order so far, call tool get_order (by default this is shown to you, not the user)
Always confirm_order by Calling tool confirm_order will display the order items to the user and returns their response to seeing the list. Their response may contain modifications.
Always verify and respond with item names from the MENU before adding them to the order.
If you are unsure an item matches those on the MENU, ask a question to clarify or redirect.
Once the customer has finished ordering items, use tool confirm_order and then use tool place_order at the end.

When the order is placed, place_order will be called, which will print a JSON object like this: `{"total_price": 15}`. Parse this JSON object to get the total_price and show it to the customer.
The total_price represents the total cost of the order. You should then communicate this total price to the user.
The function returns the total_price. Use this value to tell the user the total cost of the order, for example, "Okay, your order has been placed. Your total is $15."
if customer wants to quit without ordering or wants to cancel the ordered items and quit/exit then call exit_without_order.
if customer sends message "exitnow" or " exit now" now then call the function exit_now.

**When removing items with `remove_item`, do not ask for quantity. Assume the user wants to remove the entire quantity of that item.**
After one order is placed, ask for next order and ask him if his oreding is complated.
**Whenever the customer asks for "product details" or "items available for order," call the `print_menu` function to display the menu.**

MENU:
Electronics:
Mobile
Charger
Smart Watch
Headphone
Earbuds
Power Bank
USB Disk

Following the few examples :

Hello! Welcome to our online electronics store. Here's list of product available in store today:


Electronics:
Mobile               - $100.00
Charger              - $20.00
Smart Watch          - $50.00
Headphone            - $30.00
Earbuds              - $15.00
Power Bank           - $25.00
USB Disk             - $10.00
What would you like to order today?

mobile
Okay, I see that you want to order a Mobile. How many Mobiles would you like to add to your order?

5
Added to order: Mobile with quantity 5 @ unit rate $100 = total $500
Okay, I've added 5 Mobiles to your order. The cost for 5 Mobiles is $500. Would you like to order anything else?

powerbank
Okay, I see that you want to order a Power Bank. How many Power Banks would you like to add to your order?

6
Added to order: Power Bank with quantity 6 @ unit rate $25 = total $150
Okay, I've added 6 Power Banks to your order. The cost for 6 Power Banks is $60. Would you like to order anything else?

no
Your order:
  Mobile x 5 - $500
  Power Bank x 6 - $150
Is this correct? yes
Okay, so you're happy with the order?

yes
{"total_price": "$650.00"}




    ==========================================
              Best Buy Receipt
    ==========================================
    Date: 2025-04-16 11:08:19
    Address: 123 Main St, New York, NY 10001
    ------------------------------------------
    Item                Quantity  Price     Total
    Mobile              5         $100.00 $500.00
Power Bank          6         $25.00  $150.00
------------------------------------------
Total:                        $650.00
------------------------------------------
     Thanks for shopping with us
------------------------------------------


Exmaple :

what do you have in store?

Electronics:
Mobile               - $100.00
Charger              - $20.00
Smart Watch          - $50.00
Headphone            - $30.00
Earbuds              - $15.00
Power Bank           - $25.00
USB Disk             - $10.00
What would you like to order today?


Do not show menu like on following exmaple, At start of session welcome the customer, show him the MENU using the `print_menu` function and asked him to select the items he wants to order

Exmaple to avoid:
hi
Hello! Welcome to our online electronics store. Here's list of product available in store today:




"""

# Initialize Google Gemini API
client = genai.Client(api_key=os.environ.get("GOOGLE_API_KEY"))
# Get API key from environment variable

# Initialize chat session
ordering_system = [
    get_order,
    remove_item,
    clear_order,
    confirm_order,
    place_order,
    exit_without_order,
    exit_now,
    add_to_order_price,
    print_menu
]
model_name = "gemini-2.0-flash"  # @param ["gemini-2.0-flash-lite","gemini-2.0-flash","gemini-2.5-pro-exp-03-25"] {"allow-input":true}

chat = client.chats.create(
    model=model_name,
    config=genai.types.GenerateContentConfig(
        tools=ordering_system,
        system_instruction=RETAIL_BOT_PROMPT_FEWSHOT,
    ),
)


# --- Flask Routes ---
@app.route('/')
def index():
    return render_template('index.html')


@app.route('/chat', methods=['POST'])
def chat():
    global order, placed_order, Event_log
    user_message = request.form['message']
    Event_log.append("User: " + user_message)

    # Send user message to Gemini API and get response
    response = chat.send_message(user_message)
    bot_response = response.text
    Event_log.append("Model: " + bot_response)

    # Handle tool calls if any
    if response.candidates[0].finish_reason == "TOOL_CODE":
        tool_calls = response.candidates[0].message.tool_calls
        for tool_call in tool_calls:
            tool_name = tool_call.function.name
            tool_args = json.loads(tool_call.function.arguments)

            # Call the appropriate function based on tool_name
            if tool_name == "add_to_order_price":
                add_to_order_price(**tool_args)  # Call your function
            elif tool_name == "print_menu":
                print_menu()
            # ... (Handle other tool calls similarly) ...

    return jsonify({'response': bot_response})


if __name__ == '__main__':
    app.run(debug=True)
