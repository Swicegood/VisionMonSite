import os

# Database configuration
DB_HOST = os.getenv('DB_HOST', '192.168.0.71')
DB_NAME = os.getenv('DB_NAME', 'visionmon')
DB_USER = os.getenv('DB_USER', 'pguser')
DB_PASSWORD = os.getenv('DB_PASSWORD', 'pgpass')

# Redis configuration
REDIS_HOST = os.getenv('REDIS_HOST', '192.168.0.71')
REDIS_PORT = int(os.getenv('REDIS_PORT', 6379))
ALERT_QUEUE = os.getenv('ALERT_QUEUE', 'alert_queue')

DAILY_SUMMARY = os.getenv('DAILY_SUMMARY', 'true')
if DAILY_SUMMARY.lower() == 'true':
    DAILY_SUMMARY = True
else:
    DAILY_SUMMARY = False

DISCORD_WEBHOOK_URL = os.getenv('DISCORD_WEBHOOK_URL', '')

# Camera information - Reduced to 8 cameras for faster processing
camera_names = {
    "rHWz9GRDFxrOZF7b": "Down_Pujari",
    "5SJZivf8PPsLWw2n": "Hall",
    "g8rHNVCflWO1ptKN": "Kitchen",
    "iY9STaEt7K9vS8yJ": "Prabhupada",
    "IOKAu7MMacLh79zn": "Temple",
    "sHlS7ewuGDEd2ef4": "Up_Pujari",
    "AXIS_ID": "Axis",
    "prXH5H6e9GxOij1Z": "Front_Driveway"
}

camera_indexes = {
    'rHWz9GRDFxrOZF7b': 1,  # Down_Pujari
    '5SJZivf8PPsLWw2n': 2,  # Hall
    'g8rHNVCflWO1ptKN': 3,  # Kitchen
    'iY9STaEt7K9vS8yJ': 4,  # Prabhupada
    'IOKAu7MMacLh79zn': 5,  # Temple
    'sHlS7ewuGDEd2ef4': 6,  # Up_Pujari
    'AXIS_ID': 7,           # Axis
    'prXH5H6e9GxOij1Z': 8   # Front_Driveway
}

camera_descriptions = {
    "Down_Pujari": "The area downstairs where pujaris prepare dresses for the deiteis, typically only occupied by pujaris.",
    "Hall": "Dining and event hall, typically used for prasadam distribution, classes, or gatherings. May be occupied by visitors or devotees.",
    "Kitchen": "The temple kitchen, typically used for cooking prasadam or preparing food. May be occupied by kitchen staff or pujaris.",
    "Prabhupada": "The main hall of the temple, typically used for kirtans, classes, or gatherings. May be occupied by visitors or devotees. There is a statue of Srila Prabhupada in this area.",
    "Temple": "The main hall of the temple, typically used for kirtans, classes, or gatherings. May be occupied by visitors or devotees.",
    "Up_Pujari": "The upstairs area where pujaris prepare dresses for the deities, typically only occupied by pujaris.",
    "Axis": "External camera view.",
    "Front_Driveway": "The front driveway of the temple."
}