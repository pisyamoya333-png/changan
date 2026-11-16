import httpx
import uuid

from config import payment_api_token, payment_url


async def create_invoice(amount: float, asset: str = "USDT", allow_anonymous: bool = False, expires_in: int = 180):
    url = f"{payment_url}/createInvoice"
    headers = {"Crypto-Pay-API-Token": payment_api_token}
    json = {
        "amount": amount, 
        "asset": asset,
        "allow_anonymous": allow_anonymous,
        "expires_in": expires_in 
    }  
    async with httpx.AsyncClient() as client:
        response = await client.post(url, json=json, headers=headers)
        if response.status_code == 200 and response.json().get("ok"):
            return response.json()["result"]["pay_url"]
        else:
            raise Exception("Не удалось создать счёт: ", response.text)
        

async def get_balance():
    url = f"{payment_url}/getBalance"
    headers = {"Crypto-Pay-API-Token": payment_api_token}
    async with httpx.AsyncClient() as client:
        response = await client.post(url, headers=headers)
        if response.status_code == 200 and response.json().get("ok"):
            result = response.json()['result']
            for item in result:
                if item['currency_code'] == 'USDT':
                    return item['available']
        else:
            raise Exception("Не удалось получить баланс: ", response.text)
        

async def transfer(user_id: int, amount: float, asset: str = "USDT"):
    url = f"{payment_url}/transfer"
    headers = {"Crypto-Pay-API-Token": payment_api_token}
    spend_id = str(uuid.uuid4())
    json = {
        "user_id": user_id,
        "asset": asset,
        "amount": amount,
        "spend_id": spend_id
    }  
    async with httpx.AsyncClient() as client:
        response = await client.post(url, json=json, headers=headers)
        if response.status_code == 200 and response.json().get("ok"):
            return response.json()["result"]
        else:
            raise Exception("Не удалось выполнить перевод: ", response.text)


async def create_check(amount: float, asset: str = "USDT"):
    url = f"{payment_url}/createCheck"
    headers = {"Crypto-Pay-API-Token": payment_api_token}
    json = {
        "amount": amount, 
        "asset": asset
    }  
    async with httpx.AsyncClient() as client:
        response = await client.post(url, json=json, headers=headers)
        if response.status_code == 200 and response.json().get("ok"):
            return [response.json()["result"]["bot_check_url"], response.json()["result"]["check_id"]]
        else:
            raise Exception("Не удалось создать чек: ", response.text)
        

async def delete_check(check_id: int):
    url = f"{payment_url}/deleteCheck"
    headers = {"Crypto-Pay-API-Token": payment_api_token}
    json = {
        "check_id": check_id
    }  
    async with httpx.AsyncClient() as client:
        response = await client.post(url, json=json, headers=headers)
        if response.status_code == 200 and response.json().get("ok"):
            return response.json()["result"]
        else:
            raise Exception("Не удалось удалить чек: ", response.text)