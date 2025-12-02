import asyncio
from schemas import RegisterUserData
from tools import get_wd, get_number, register_number, save_number

if __name__ == "__main__":
    while True:
        number = get_number()
        
        if not number:
            print("Не удалось получить номер. Проверьте доступ к SMS-Activate API")
            print("Возможные причины:")
            print("- Доступ заблокирован для вашей страны (используйте VPN)")
            print("- Недостаточно средств на балансе")
            print("- Нет доступных номеров")
            break
            
        wd = get_wd(no_reset=False)
        number = register_number(wd, number, RegisterUserData(first_name="Artem"))
        
        if number:
            asyncio.run(save_number(wd, number))
            break
        else:
            print("Регистрация не удалась, пробуем следующий номер...")
