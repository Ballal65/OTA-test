from modbus import read_modbus_data
from wifi import connect_to_internet, process_ap_mode
from mqtt import connect_to_mqtt
import machine, time, json

#Test Comment for OTA
button_pin = 26

client = None
topic = "AIDHOOSTATION"

watchdog = machine.WDT(timeout = 60000)
#----------------------AP MODE BUTTON ------------------------------
def button_pressed(pin):
    print("Button Pressed! Entering AP Mode")
    process_ap_mode()

# Wifi button Interrupt
button = machine.Pin(button_pin, machine.Pin.IN, machine.Pin.PULL_UP)
button.irq(trigger=machine.Pin.IRQ_FALLING, handler=button_pressed)

#----------------------RAIN CODE ------------------------------
rain_bucket_pin = 21
count = 0
last_rain_time = 0  # Keep track of the last time rain was detected
last_reset_date = None  # Store the last reset date
reset_interval = 15 * 60 * 1000 #30 mins in milliseconds

def save_count_to_file():
    data = {"count": count}
    with open("rain_count.json", "w") as file:
        json.dump(data, file)
        
def reset_daily_count(timer):
    global count, last_reset_date
    current_date = time.localtime()[2]  # Day of the month
    if last_reset_date is None or last_reset_date != current_date:
        count = 0
        last_reset_date = current_date
        print("Daily count reset.")
        save_count_to_file()

def rain_input(pin):
    global count, last_rain_time
    current_time = time.ticks_ms()  # Get current time in milliseconds
    if current_time - last_rain_time > 1500:  # Debounce by checking time difference
        count += 1
        last_rain_time = current_time
        print(f"Rain detected. Current count is: {count}")
        save_count_to_file()

# Configure pin 21 as an input with an interrupt for rain detection
rain_bucket = machine.Pin(rain_bucket_pin, machine.Pin.IN, machine.Pin.PULL_UP)
rain_bucket.irq(trigger=machine.Pin.IRQ_RISING, handler=rain_input)

# Create a timer to reset the count every 30 minutes
reset_timer = machine.Timer(-1)
reset_timer.init(period=reset_interval, mode=machine.Timer.PERIODIC, callback=reset_daily_count)


while True:
    try:
        connect_to_internet()
        watchdog.feed()
        if connect_to_internet():
            if client is None:
                client = connect_to_mqtt()
            client.check_msg()
        else:
            client = None
            time.sleep(15)
            machine.reset()
        sensor_data = read_modbus_data()
        message = json.dumps(sensor_data)
        client.publish(topic, message)
        time.sleep(10)
        
    except KeyboardInterrupt:
        print('KeyboardInterrupt, stopping RTU client...')
        break
    except Exception as e:
        print('Exception during execution: {}'.format(e))
        
