BASE_URL = "https://solar.siseli.com"
DEFAULT_TIMEOUT = 30.0
DEFAULT_PAGE_SIZE = 20
# dataSource=1 observed in all telemetry requests in HAR captures
DEFAULT_DATA_SOURCE = 1

# Siseli Open API application credentials extracted from the official web
# client. The secret is only obfuscated (AES key derived from the public app
# id), NOT confidential: treat it as a public constant of the vendor's web
# app, and note the vendor may rotate it. Override per client with
# ``SiseliClient(open_auth=(app_id, encrypted_secret))`` if it changes.
SISELI_APP_ID = "rBrTRfAPXz"
SISELI_APP_SECRET_ENCRYPTED = "I4D0KRr2339z3pQ/at91V9BpFAOe54DaTafwSm6suIQ="  # noqa: S105
