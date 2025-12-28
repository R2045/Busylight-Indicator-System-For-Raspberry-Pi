import RPi.GPIO as GPIO
from flask import Flask, request, jsonify
from flask_cors import CORS
import threading
import time

# --- CONFIGURATION ---
GREEN_LED = 17  # GPIO Pin 17
YELLOW_LED = 27 # GPIO Pin 27
RED_LED = 22    # GPIO Pin 22

# --- GLOBAL STATE ---
current_led_state = "available" 
lock = threading.Lock()

app = Flask(__name__)
CORS(app) 

# --- GPIO SETUP ---
def setup_gpio():
    GPIO.setmode(GPIO.BCM)
    GPIO.setwarnings(False)
    pins = [GREEN_LED, YELLOW_LED, RED_LED]
    for pin in pins:
        GPIO.setup(pin, GPIO.OUT, initial=GPIO.LOW)

def set_leds(green, yellow, red):
    """Helper to set all 3 LEDs at once."""
    GPIO.output(GREEN_LED, GPIO.HIGH if green else GPIO.LOW)
    GPIO.output(YELLOW_LED, GPIO.HIGH if yellow else GPIO.LOW)
    GPIO.output(RED_LED, GPIO.HIGH if red else GPIO.LOW)

# --- LED ANIMATION ENGINE ---
def led_control_loop():
    global current_led_state
    led_toggle = True # Used for blinking logic
    
    while True:
        with lock:
            state = current_led_state
        
        if state == "available":
            # SOLID GREEN
            set_leds(True, False, False)
            time.sleep(0.5)
            
        elif state == "busy-talkable":
            # FAST BLINK YELLOW (0.2s)
            if led_toggle:
                set_leds(False, True, False)
            else:
                set_leds(False, False, False)
            led_toggle = not led_toggle
            time.sleep(0.2)
            
        elif state == "dnd":
            # SLOW BLINK RED (0.8s)
            if led_toggle:
                set_leds(False, False, True)
            else:
                set_leds(False, False, False)
            led_toggle = not led_toggle
            time.sleep(0.8)

        elif state == "off":
            set_leds(False, False, False)
            time.sleep(1.0)

# --- API ENDPOINTS ---

@app.route('/set_led', methods=['POST'])
def set_led_route():
    """Update the status from a remote device."""
    global current_led_state
    data = request.json
    status = data.get('status')
    
    valid_statuses = ["available", "busy-talkable", "dnd", "off"]
    
    if status in valid_statuses:
        with lock:
            current_led_state = status
        print(f"Status updated to: {status}")
        return jsonify({"success": True, "new_status": status})
    
    return jsonify({"success": False, "error": "Invalid status"}), 400

@app.route('/get_status', methods=['GET'])
def get_status_route():
    """Allows other devices to see what the current status is."""
    with lock:
        return jsonify({"status": current_led_state})

# --- MAIN ---
if __name__ == '__main__':
    setup_gpio()
    print("--- Status Hub Server Started ---")
    print(f"Green: GPIO {GREEN_LED} (Solid)")
    print(f"Yellow: GPIO {YELLOW_LED} (Fast Blink)")
    print(f"Red: GPIO {RED_LED} (Slow Blink)")
    
    # Start the LED animation thread
    threading.Thread(target=led_control_loop, daemon=True).start()
    
    # Run Flask server on all network interfaces (0.0.0.0)
    try:
        app.run(host='0.0.0.0', port=5000)
    except KeyboardInterrupt:
        print("\nShutting down...")
    finally:
        GPIO.cleanup()
