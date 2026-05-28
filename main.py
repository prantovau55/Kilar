from fastapi import FastAPI
from pydantic import BaseModel
import re
import random
import httpx
from typing import Optional

app = FastAPI(title="Ultimate CC Suite API")

class CardRequest(BaseModel):
    card_number: str

class GenRequest(BaseModel):
    bin_number: str
    quantity: int = 5

def luhn_check(card_num: str) -> bool:
    total = 0
    reverse_digits = card_num[::-1]
    for i, digit in enumerate(reverse_digits):
        n = int(digit)
        if i % 2 == 1:  # রিভার্স করার পর প্রতি ২য় ডিজিট গুণ হবে
            n *= 2
            if n > 9:
                n -= 9
        total += n
    return total % 10 == 0

# লাইভ বিন চেকার (Real-time Bank & Country Info)
async def get_bin_info(card_num: str) -> dict:
    bin_6 = card_num[:6]
    async with httpx.AsyncClient() as client:
        try:
            # Binlist এর ফ্রি লিমিট শেষ হলে এই API-টি ট্রাই করতে পারেন
            response = await client.get(f"https://lookup.binlist.net/{bin_6}", headers={'Accept-Version': '3'}, timeout=5.0)
            if response.status_code == 200:
                data = response.json()
                return {
                    "scheme": data.get("scheme", "Unknown").upper(),
                    "type": data.get("type", "Unknown").upper(),
                    "brand": data.get("brand", "Unknown").upper(),
                    "country": data.get("country", {}).get("name", "Unknown 🏳️"),
                    "bank": data.get("bank", {}).get("name", "Unknown Bank 🏦")
                }
        except Exception:
            pass
    return {"scheme": "Unknown", "type": "Unknown", "brand": "Unknown", "country": "Unknown", "bank": "Unknown"}

@app.post("/api/v1/check")
async def check_card(data: CardRequest):
    clean_num = re.sub(r'\D', '', data.card_number)
    if len(clean_num) < 13 or len(clean_num) > 19:
        return {"status": "error", "message": "Invalid length"}
        
    is_valid = luhn_check(clean_num)
    info = await get_bin_info(clean_num)
    
    return {
        "status": "success",
        "card": clean_num,
        "valid": is_valid,
        "bin": clean_num[:6],
        **info
    }

@app.post("/api/v1/generate")
def gen_card(data: GenRequest):
    bin_str = re.sub(r'\D', '', data.bin_number)
    
    # বিন যদি ৬ ডিজিটের কম হয় তবে র্যান্ডম সংখ্যা দিয়ে ৬ ডিজিট করা
    while len(bin_str) < 6: 
        bin_str += str(random.randint(0, 9))
    
    qty = min(data.quantity, 30) # সর্বোচ্চ ৩০টি
    generated_cards = []
    
    for _ in range(qty):
        # একটি স্ট্যান্ডার্ড ১৬ ডিজিটের কার্ডের জন্য ১৫টি ডিজিট তৈরি করা (১টি বাকি রাখা চেক ডিজিটের জন্য)
        cc_num = bin_str
        while len(cc_num) < 15:
            cc_num += str(random.randint(0, 9))
            
        # Luhn Check Digit Generation (সঠিক লজিক)
        sum_val = 0
        reverse_digits = cc_num[::-1]
        for i, digit in enumerate(reverse_digits):
            n = int(digit)
            if i % 2 == 0:  # এখানে ০ হবে, কারণ আমরা অলরেডি ১টি ডিজিট কম নিয়েছি (যা শেষে বসবে)
                n *= 2
                if n > 9: 
                    n -= 9
            sum_val += n
            
        check_digit = (10 - (sum_val % 10)) % 10
        final_card = cc_num + str(check_digit)
        
        month = f"{random.randint(1, 12):02d}"
        year = str(random.randint(2026, 2032)) # ২০২৬ থেকে ২০৩২ এর মধ্যে
        cvv = f"{random.randint(100, 999)}"
        
        generated_cards.append(f"{final_card}|{month}|{year}|{cvv}")
        
    return {"status": "success", "bin": bin_str[:6], "quantity": qty, "cards": generated_cards}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000) # হোস্টিংয়ের জন্য host="0.0.0.0" দেওয়া ভালো
  
