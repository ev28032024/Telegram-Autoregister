import logging
import os
import re
import time
import json
import requests
from typing import Optional, List, Dict, Any, Union
from pathlib import Path
from datetime import datetime, timezone

# Импорты для Appium/Telethon (оставлены без изменений)
from appium import webdriver
from appium.options.common import AppiumOptions
from appium.webdriver.common.appiumby import AppiumBy
from telethon import TelegramClient
from appium.webdriver.webelement import WebElement as MobileWebElement

# Импорты из вашего проекта
from schemas import NumberGet, RegisterUserData
from settings import (SMS_ACTIVATE_API_KEY, DEVICE_NAME, APPIUM_SERVER_URL,
                      APP_API_ID, APP_API_HASH, APP_PACKAGE,
                      USE_PROXY, PROXY_HTTP, PROXY_HTTPS)


# --- Настройка логгера и констант ---

logging.basicConfig(level=logging.INFO, format='%(levelname)s:%(name)s:%(message)s')
logger = logging.getLogger('Tools')
logger.setLevel(logging.INFO)

# API Endpoint для SMS-Activate
SMS_API_URL = "https://sms-activate.org/stubs/handler_api.php"

# Определение корневой папки проекта
PROJECT_ROOT = Path(__file__).resolve().parent
ACTIVATIONS_FILE: Path = PROJECT_ROOT / "activations.json"

# Минимальная цена для фильтрации (для обхода NO_BALANCE на дешевых номерах)
MIN_PRICE_FILTER = 2.0

# Полный список кодов стран для Telethon
PREFIX_BY_NAME = {
    # ... (список стран)
    "Palestine": "970", "Nicaragua": "505", "Grenada": "1473", "Malawi": "265", "Uganda": "256",
    "Bolivia": "591", "Paraguay": "595", "Kenya": "254", "Tanzania": "255", "Morocco": "212",
    "Ethiopia": "251", "Mozambique": "258", "Tunisia": "216", "Kuwait": "965", "Jamaica": "1",
    "Oman": "968", "Central African Republic": "236", "Dominica": "1767", "Guyana": "592", "Rwanda": "250",
    "Zambia": "260", "Mali": "223", "Iceland": "354", "Canada": "1", "Mongolia": "976",
    "Papua New Guinea": "675", "Sudan": "249", "Libya": "218", "Trinidad and Tobago": "1", "Swaziland": "268",
    "Sierra Leone": "232", "Lesotho": "266", "Reunion": "262", "Somalia": "252", "Burkina Faso": "226",
    "Lebanon": "961", "Gabon": "241", "Maldives": "960", "French Guiana": "594", "Saint Lucia": "1",
    "Equatorial Guinea": "240", "Eritrea": "291", "Aruba": "297", "Montserrat": "1", "Anguilla": "1",
    "Seychelles": "248", "Namibia": "264", "Philippines": "63", "Indonesia": "62", "Ivory Coast": "225",
    "Chad": "235", "Zimbabwe": "263", "Ecuador": "593", "Qatar": "974", "Panama": "507",
    "Mauritania": "222", "Barbados": "1", "Burundi": "257", "Bahamas": "1", "Belize": "501",
    "Guinea-Bissau": "245", "Comoros": "269", "Saint Kitts and Nevis": "1", "Tajikistan": "992", "Bahrain": "973",
    "Vietnam": "84", "Macao": "853", "Gambia": "220", "Cameroon": "237", "Guinea": "224",
    "Angola": "244", "DR Congo": "243", "Nigeria": "234", "Algeria": "213", "Sri Lanka": "94",
    "Syria": "963", "Botswana": "267", "Niger": "227", "Mauritius": "230", "Dominican Republic": "1",
    "Togo": "228", "Uruguay": "598", "Guadeloupe": "590", "Turkmenistan": "993", "Saint Vincent and the Grenadines": "1",
    "Antigua and Barbuda": "1", "Cayman Islands": "1", "Sao Tome and Principe": "239", "New Caledonia": "687", "Cape Verde": "238",
    "Malaysia": "60", "Laos": "856", "Yemen": "967", "South Africa": "27", "Colombia": "57",
    "Iraq": "964", "Saudi Arabia": "966", "Timor-Leste": "670", "Liberia": "231", "Armenia": "374",
    "Chile": "56", "Bhutan": "975", "Norway": "47", "USA": "1", "Hong Kong": "852",
    "Pakistan": "92", "Georgia": "995", "Argentina": "54", "Peru": "51", "Venezuela": "58",
    "Congo": "242", "Afghanistan": "93", "Honduras": "504", "Guatemala": "502", "Jordan": "962",
    "South Sudan": "211", "Kosovo": "383", "Cambodia": "855", "Brazil": "55", "Benin": "229",
    "North Macedonia": "389", "Niue": "683", "India": "91", "Israel": "972", "United Kingdom": "44",
    "China": "86", "Serbia": "381", "Uzbekistan": "998", "Austria": "43", "Thailand": "66",
    "Mexico": "52", "Iran": "98", "Slovenia": "386", "Salvador": "503", "Bosnia": "387",
    "Puerto Rico": "1", "Turkey": "90", "Croatia": "385", "Bangladesh": "880", "Slovakia": "421",
    "Estonia": "372", "Albania": "355", "Kazakhstan": "7", "Lithuania": "370", "Spain": "34",
    "Cyprus": "357", "Bulgaria": "359", "Portugal": "351", "Moldova": "373", "Poland": "48",
    "Romania": "40", "New Zealand": "64", "Germany": "49", "Ireland": "353", "Netherlands": "31",
    "Cuba": "53", "Japan": "81", "Malta": "356", "Ukraine": "380", "Sweden": "46",
    "UAE": "971", "Switzerland": "41", "Australia": "61", "Italy": "39", "France": "33",
    "Belgium": "32", "Singapore": "65", "Egypt": "20"
}


# --- Утилиты для API и прокси ---

def get_session() -> requests.Session:
    """Создает и настраивает сессию requests с прокси."""
    session = requests.Session()
    if USE_PROXY and PROXY_HTTP and PROXY_HTTPS:
        proxies = {
            'http': PROXY_HTTP,
            'https': PROXY_HTTPS
        }
        session.proxies.update(proxies)
        logger.info(f"✓ Прокси настроен для API: {PROXY_HTTP.split('@')[-1] if '@' in PROXY_HTTP else PROXY_HTTP}")
    else:
        logger.info("⚠ Прокси не используется для API")
    return session

def request_sms_api(action: str, params: Optional[Dict[str, Union[str, int]]] = None) -> Optional[str]:
    """Универсальная функция для отправки запросов к SMS-Activate API."""
    session = get_session()
    
    # Базовые параметры
    payload = {
        'api_key': SMS_ACTIVATE_API_KEY,
        'action': action,
        ** (params if params else {})
    }
    
    try:
        response = session.get(SMS_API_URL, params=payload, timeout=15)
        response.raise_for_status() # Вызывает исключение для 4xx/5xx ошибок
        
        response_text = response.text.strip()
        
        # Общая проверка на ошибку
        if response_text.startswith('ERROR:'):
            error_code = response_text.split('ERROR:')[1].strip()
            logger.error(f"API Error: {error_code}")
            return None
            
        # Общая проверка на блокировку (ответ не в JSON/тексте)
        if len(response_text) < 5 and not response_text.startswith('ACCESS'):
            logger.error(f"API вернуло слишком короткий/неизвестный ответ: {response_text!r}. Возможна блокировка прокси.")
            return None
            
        return response_text
        
    except requests.exceptions.HTTPError as e:
        logger.error(f"HTTP Error при запросе {action}: {e}")
    except requests.exceptions.ConnectionError as e:
        logger.error(f"Connection Error (проверьте прокси/VPN) при запросе {action}: {e}")
    except requests.exceptions.Timeout:
        logger.error(f"Timeout при запросе {action}.")
    except Exception as e:
        logger.error(f"Неизвестная ошибка при запросе {action}: {e}")
        
    return None

def get_api_balance() -> float:
    """Получает текущий баланс."""
    response_text = request_sms_api("getBalance")
    if not response_text:
        return 0.0
    
    # Ожидаемый ответ: ACCESS_BALANCE:10.55
    if response_text.startswith('ACCESS_BALANCE:'):
        try:
            balance = float(response_text.split(':')[1])
            return balance
        except ValueError:
            logger.error(f"Не удалось распарсить баланс из ответа: {response_text}")
            return 0.0
    
    # Обработка нестандартного ответа, который не удалось поймать request_sms_api
    logger.error(f"Неизвестный ответ API при запросе баланса: {response_text!r}")
    return 0.0

def get_countries_map() -> Optional[Dict[str, Any]]:
    """Получает карту стран для преобразования ID в имя (eng)."""
    response_text = request_sms_api("getCountries")
    if not response_text:
        return None
    
    try:
        # Ответ должен быть в JSON формате
        return json.loads(response_text)
    except json.JSONDecodeError as e:
        logger.error(f"Критическая ошибка: API вернуло не-JSON ответ при запросе стран. Проверьте прокси/IP-блокировку. Ошибка: {e}")
        return None
    except Exception as e:
        logger.error(f"Ошибка при обработке getCountries: {e}")
        return None

def get_prices(service: str) -> Dict[int, Dict[str, Union[float, int]]]:
    """Получает цены и количество для заданного сервиса."""
    response_text = request_sms_api("getPrices", {'service': service})
    if not response_text:
        return {}
        
    try:
        raw_data = json.loads(response_text)
        prices = {}
        # Формат: {'7': {'tg': {'cost': '50', 'count': 5}}}
        for country_str, services in raw_data.items():
            if service in services:
                prices[int(country_str)] = {
                    'price': float(services[service]['cost']), 
                    'count': int(services[service]['count'])
                }
        return prices
    except json.JSONDecodeError:
        logger.error(f"Не удалось распарсить цены из ответа: {response_text!r}")
        return {}
    except Exception as e:
        logger.error(f"Ошибка при обработке getPrices: {e}")
        return {}


# --- Вспомогательные функции JSON-реестра (без изменений) ---

def _load_activations() -> List[Dict[str, Any]]:
    # ... (код функции _load_activations)
    if not ACTIVATIONS_FILE.exists():
        return []
    try:
        with open(ACTIVATIONS_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
        if isinstance(data, list):
            return data
    except Exception:
        logger.exception("Не удалось прочитать файл активаций %s", ACTIVATIONS_FILE)
    return []

def _save_activations(data: List[Dict[str, Any]]) -> None:
    # ... (код функции _save_activations)
    try:
        ACTIVATIONS_FILE.parent.mkdir(parents=True, exist_ok=True)
        with open(ACTIVATIONS_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=4)
    except Exception:
        logger.exception("Не удалось записать файл активаций %s", ACTIVATIONS_FILE)

def save_activation_to_json(activation_id: str, phone_number: str) -> None:
    # ... (код функции save_activation_to_json)
    data = _load_activations()
    now = datetime.now(timezone.utc).isoformat()
    data.append(
        {
            "activation_id": str(activation_id),
            "phone_number": str(phone_number),
            "created_at": now,
        }
    )
    _save_activations(data)
    logger.info("Отслеживается активация %s для номера %s", activation_id, phone_number)

def remove_activation_from_json(activation_id: str) -> None:
    # ... (код функции remove_activation_from_json)
    data = _load_activations()
    before = len(data)
    data = [row for row in data if str(row.get("activation_id")) != str(activation_id)]
    after = len(data)
    _save_activations(data)
    if before != after:
        logger.info("Удалена активация %s из реестра (было: %s, стало: %s).", activation_id, before, after)

def can_set_status_8(activation_id: str, min_age_seconds: int = 120) -> bool:
    # ... (код функции can_set_status_8)
    data = _load_activations()
    for row in data:
        if str(row.get("activation_id")) != str(activation_id):
            continue
        created_at = row.get("created_at")
        if not created_at:
            return True 
        try:
            created_dt = datetime.fromisoformat(created_at).replace(tzinfo=timezone.utc)
        except ValueError:
            return True
        
        age = (datetime.now(timezone.utc) - created_dt).total_seconds()
        
        if age >= min_age_seconds:
            return True
    
    return False


# --- Основная логика получения номера и СМС ---

def cancel_activation(activation_id: str):
    """Безопасная отмена активации (статус 8) с проверкой возраста."""
    if not can_set_status_8(activation_id):
        logger.warning(f"Отмена ID {activation_id} отложена (еще не прошло 120 сек. с резервации).")
        return False

    logger.info(f"Отмена активации ID {activation_id} (статус 8)...")
    response_text = request_sms_api("setStatus", {'id': activation_id, 'status': 8})
    
    if response_text and "ACCESS" in response_text:
        logger.info(f"✓ Установлен статус 8 (CANCEL) для ID {activation_id}.")
        remove_activation_from_json(activation_id)
        return True
    else:
        logger.warning(f"Ошибка установки статуса 8 для ID {activation_id}: {response_text!r}")
        return False

def get_number(service="tg", max_price: int = 100) -> Optional[NumberGet]:
    
    balance = get_api_balance()
    logger.info(f"Баланс аккаунта: {balance}")
    if balance < MIN_PRICE_FILTER:
        logger.error(f"Баланс ({balance}) недостаточен или не получен. Работа остановлена.")
        return None

    logger.info(f"Установлен лимит цены: {max_price} RUB, минимальный порог: {MIN_PRICE_FILTER} RUB")
    
    countries_map = get_countries_map()
    if not countries_map:
        logger.error("Не удалось получить список стран.")
        return None
        
    prices = get_prices(service)
    avail = []

    # Фильтрация доступных стран
    for country_id_str, info in countries_map.items():
        country_id = int(country_id_str)
        country_name = info.get('eng')
        
        if country_id not in prices or not country_name:
            continue
            
        price = prices[country_id]['price']
        count = prices[country_id]['count']

        if count > 0 and price <= max_price and price >= MIN_PRICE_FILTER:
            avail.append({
                'id': country_id, 
                'name': country_name, 
                'price': price, 
                'count': count
            })
    
    avail.sort(key=lambda x: x['price'])
    
    if not avail:
        logger.error(f"Нет доступных стран с номерами для {service}, удовлетворяющих фильтрам.")
        return None

    logger.info(f"Найдено {len(avail)} стран. Топ-5 самых дешевых:")
    for a in avail[:5]:
        logger.info(f"   {a['name']} (ID {a['id']}): {a['price']} RUB, {a['count']} шт.")

    # Запрос номера
    for a in avail:
        logger.info(f"Попытка запроса номера: {a['name']} (ID {a['id']}, Цена ~{a['price']})")
        
        params = {'service': service, 'country': a['id']}
        response_text = request_sms_api("getNumber", params)
        
        if response_text and response_text.startswith('ACCESS_NUMBER:'):
            # Успех: ACCESS_NUMBER:ID_АКТИВАЦИИ:НОМЕР_ТЕЛЕФОНА
            parts = response_text.split(':')
            activation_id = parts[1]
            full_phone = parts[2]
            name = a['name']
            prefix = PREFIX_BY_NAME.get(name, "")
            
            # Логика очистки номера от префикса
            pn = full_phone.replace(prefix, '', 1) if full_phone.startswith(prefix) else full_phone
            
            save_activation_to_json(activation_id, full_phone)
            logger.info(f"✓ УСПЕХ! Получен номер: {full_phone} (ID: {activation_id})")
            
            return NumberGet(activation_id=activation_id, full_phone_number=full_phone, phone_number=pn, country_code=prefix)
        
        elif response_text and 'NO_NUMBERS' in response_text:
            logger.warning(f"Нет номеров для {a['name']}. Пробуем следующую.")
        elif response_text and 'NO_BALANCE' in response_text:
             logger.error(f"Баланс стал недостаточным. Останавливаем работу.")
             return None
        
        time.sleep(1) # Небольшая задержка между запросами
    
    logger.error("Не удалось получить номер (перебрали все доступные страны)")
    return None

def get_sms(activation_id: str) -> Optional[str]:
    
    timeout = 90
    poll_interval = 5
    deadline = time.time() + timeout
    
    logger.info(f"Начинаем ожидание СМС для ID {activation_id} (до 5 минут)")
    
    while time.time() < deadline:
        response_text = request_sms_api("getStatus", {'id': activation_id})
        
        if response_text and response_text.startswith('STATUS_OK:'):
            # Успех: STATUS_OK:КОД_ИЗ_СМС
            code = response_text.split(':')[1].strip()
            logger.info(f"✓ Получен SMS код для ID {activation_id}")
            
            # Завершаем активацию (status=6)
            set_final_status(activation_id, 6)
            remove_activation_from_json(activation_id)
            
            return code
        
        elif response_text and response_text == 'STATUS_WAIT_CODE':
            logger.debug("Ожидание СМС...")
            
        elif response_text and response_text == 'STATUS_CANCEL':
            logger.warning("Активация была отменена провайдером/скриптом.")
            remove_activation_from_json(activation_id)
            return None

        elif response_text and response_text in ('NO_ACTIVATION', 'BAD_SERVICE', 'BAD_STATUS'):
            logger.error(f"Критическая ошибка статуса {activation_id}: {response_text}")
            remove_activation_from_json(activation_id)
            return None

        time.sleep(poll_interval)
    
    # Таймаут достигнут
    logger.warning("Время ожидания СМС истекло.")
    # Отменяем активацию, чтобы вернуть средства
    cancel_activation(activation_id)
    return None

def set_final_status(activation_id: str, status: int = 6):
    """Устанавливает статус завершения/отмены."""
    if status not in (6, 8):
        raise ValueError("Статус должен быть 6 (FINISH) или 8 (CANCEL)")
        
    action_name = "FINISH" if status == 6 else "CANCEL"
    response_text = request_sms_api("setStatus", {'id': activation_id, 'status': status})
    
    if response_text and "ACCESS" in response_text:
        logger.info(f"✓ Установлен статус {status} ({action_name}) для ID {activation_id}.")
        return True
    else:
        logger.warning(f"Ошибка установки статуса {status} для ID {activation_id}: {response_text!r}")
        return False


# --- Функции Appium и Telethon (оставлены без изменений) ---

# ... (Код функций Appium: get_wd, find_elements, find_element, find_by_id, find_by_text, register_number)
def get_wd(no_reset=True):
    options = AppiumOptions()
    options.load_capabilities({
        "appium:deviceName": DEVICE_NAME,
        "appium:platformName": "android",
        "appium:appPackage": APP_PACKAGE,
        "appium:appActivity": "org.telegram.messenger.DefaultIcon",
        "appium:automationName": 'uiautomator2',
        "appium:noReset": no_reset,
        "appium:autoGrantPermissions": True,
        "appium:newCommandTimeout": 0,
    })
    return webdriver.Remote(APPIUM_SERVER_URL, options=options)

def find_elements(wd: webdriver.Remote, xpath: str, max_retries=2, sleep_time=2) -> Optional[List[MobileWebElement]]:
    retries = 0
    while True:
        elements = wd.find_elements(AppiumBy.XPATH, xpath)
        if elements:
            return elements
        if retries == max_retries:
            return None
        retries += 1
        time.sleep(sleep_time)

def find_element(wd: webdriver.Remote, xpath: str, max_retries=2, sleep_time=2) -> Optional[MobileWebElement]:
    retries = 0
    while True:
        elements = wd.find_elements(AppiumBy.XPATH, xpath)
        if elements:
            return elements[0]
        if retries == max_retries:
            return None
        retries += 1
        time.sleep(sleep_time)

def find_by_id(wd: webdriver.Remote, _id: str, max_retries=2, sleep_time=2) -> Optional[MobileWebElement]:
    retries = 0
    while True:
        elements = wd.find_elements(AppiumBy.ID, _id)
        if elements:
            return elements[0]
        if retries == max_retries:
            return None
        retries += 1
        time.sleep(sleep_time)

def find_by_text(wd: webdriver.Remote, text: str, max_retries=2, sleep_time=2) -> Optional[MobileWebElement]:
    retries = 0
    while True:
        try:
            messages = wd.find_elements(AppiumBy.CLASS_NAME, 'android.widget.TextView')
            for msg in messages:
                if text.lower() in msg.text.lower():
                    return msg
            if retries == max_retries:
                return None
            retries += 1
            time.sleep(sleep_time)
        except Exception as e:
            logger.error(e)
            time.sleep(sleep_time)
            continue

def register_number(wd: webdriver.Remote, number: NumberGet, register_user_data: RegisterUserData) -> Optional[NumberGet]:
    start_messaging_btn = find_by_text(wd, "Start Messaging")
    if start_messaging_btn:
        logger.info("Найдена кнопка Start Messaging")
        start_messaging_btn.click()
    
    country_code_input = find_element(wd, '//android.widget.EditText[@content-desc="Country code"]')
    if country_code_input:
        country_code_input.clear().send_keys(number.country_code)
        
    time.sleep(3)
    
    phone_number = find_element(wd, '//android.widget.EditText[@content-desc="Phone number"]')
    if phone_number:
        phone_number.clear()
        phone_number.send_keys(number.phone_number)
        
    banned_number = find_by_text(wd, "This phone number is banned.")
    if banned_number:
        logger.error("Этот номер забанен в Telegram")
        cancel_activation(number.activation_id)
        return None
        
    logger.info("Делаем скриншот перед отправкой номера...")
    wd.save_screenshot(f"screen_before_{number.full_phone_number}.png")
    
    next_btn = find_element(wd, '//android.widget.FrameLayout[@content-desc="Done"]/android.view.View')
    if next_btn:
        next_btn.click()
    else:
        alt_next = find_element(wd, '//android.widget.FrameLayout[@content-desc="Done"]')
        if alt_next:
            alt_next.click()
        else:
            logger.error("Не найдена кнопка 'Далее' (стрелочка)")
            cancel_activation(number.activation_id)
            return None

    is_this_correct = find_by_text(wd, 'Is this the correct number?')
    if is_this_correct:
        yes_btn = find_element(wd, '//android.widget.FrameLayout[@content-desc="Done"]') or \
                  find_by_text(wd, "Yes")
        if yes_btn: yes_btn.click()
        
    digit_input = find_element(wd, '//android.widget.EditText')
    if digit_input:
        retries = 0
        while True:
            logger.info("Ждем код из СМС...")
            sms = get_sms(number.activation_id)
            if sms:
                logger.info(f"Вводим код: {sms}")
                try:
                    for index, digit in enumerate(sms):
                        field = find_element(wd, f'//android.widget.EditText[{index + 1}]', max_retries=0, sleep_time=0.1)
                        if field:
                            field.send_keys(digit)
                        else:
                            digit_input.send_keys(digit)
                            break
                except Exception as e:
                    logger.error(f"Ошибка при вводе цифр: {e}")
                break
            
            time.sleep(5)
            if retries == 60: 
                return None
            retries += 1
            
        time.sleep(3)
        your_password_label = find_by_text(wd, "Your password")
        if your_password_label:
            logger.error("Номер защищен паролем (2FA). Регистрация невозможна.")
            wd.save_screenshot(f"screen_after_{number.full_phone_number}.png")
            cancel_activation(number.activation_id)
            return None
        else:
            if os.path.exists(f"screen_before_{number.full_phone_number}.png"):
                os.remove(f"screen_before_{number.full_phone_number}.png")
                
            first_name_input = find_element(wd, "//android.widget.EditText")
            if first_name_input:
                first_name_input.send_keys(register_user_data.first_name)
                last_name_input = find_element(wd, "//android.widget.EditText[2]", max_retries=0)
                if last_name_input:
                    last_name_input.send_keys(register_user_data.last_name)
                    
                ok_btn = find_element(wd, '//android.widget.FrameLayout[@content-desc="Done"]')
                if ok_btn: ok_btn.click()
            
            tos_label = find_by_text(wd, "Terms of Service")
            if tos_label:
                tos_accept_btn = find_element(wd, "/hierarchy/android.widget.FrameLayout/android.widget.FrameLayout/android.widget.FrameLayout/android.widget.LinearLayout/android.widget.FrameLayout[2]/android.widget.TextView[2]")
                if tos_accept_btn: tos_accept_btn.click()
                
            return number
    else:
        banned_ok_btn = find_element(wd, '/hierarchy/android.widget.FrameLayout/android.widget.FrameLayout/android.widget.FrameLayout/android.widget.LinearLayout/android.widget.FrameLayout[2]/android.widget.TextView[2]')
        if banned_ok_btn:
            logger.info("Обнаружен бан номера (popup).")
            banned_ok_btn.click()
            
        internal_error_btn = find_by_text(wd, 'An internal error occurred')
        if internal_error_btn:
            logger.info("Внутренняя ошибка Telegram.")
            ok_btn = find_element(wd, '//android.widget.TextView[@text="OK"]')
            if ok_btn: ok_btn.click()

        if os.path.exists(f"screen_before_{number.full_phone_number}.png"):
            os.remove(f"screen_before_{number.full_phone_number}.png")
            
        cancel_activation(number.activation_id)
        return None

def get_code(wd: webdriver.Remote):
    telegram_btn = find_element(wd, "//android.view.ViewGroup")
    if telegram_btn:
        telegram_btn.click()
    time.sleep(2)
    
    elements = find_elements(wd, "//android.view.ViewGroup")
    if elements:
        code_el = elements[-1]
        try:
            code = re.findall(r"\d{5}", code_el.text)[0]
            logger.info(f"Код авторизации для сессии: {code}")
            return code
        except:
            logger.error("Не удалось найти 5-значный код в сообщении.")
    return None

async def save_number(wd: webdriver.Remote, number: NumberGet):
    try:
        client = TelegramClient(str(number.full_phone_number), APP_API_ID, APP_API_HASH)
        await client.start(phone=lambda: number.full_phone_number, code_callback=lambda: get_code(wd))
        
        me = await client.get_me()
        logger.info(f"Сессия успешно сохранена: {number.full_phone_number}.session (User: {me.first_name})")
        
        remove_activation_from_json(number.activation_id)
        
        await client.disconnect()
    except Exception as e:
        logger.error(f"Ошибка при сохранении сессии Telethon: {e}")
