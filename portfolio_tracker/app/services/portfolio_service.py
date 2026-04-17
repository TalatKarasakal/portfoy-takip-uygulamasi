import datetime
from typing import List, Dict, Any, Tuple
from collections import deque
from app.models.transaction import Transaction, TransactionType
from app.models.asset import Asset
from app.utils.logger import app_logger

class PortfolioService:
    @staticmethod
    def calculate_cost_and_pnl(transactions: List[Transaction], current_price: float, method: str = "WAC") -> Dict[str, Any]:
        """
        Belirtilen ortalama maliyet metoduna (WAC, FIFO, LIFO) göre ortalama maliyet, 
        gerçekleşmiş ve gerçekleşmemiş K/Z (P/L) hesaplar.
        """
        if not transactions:
            return {
                "remaining_quantity": 0,
                "average_cost": 0,
                "realized_pnl": 0,
                "unrealized_pnl": 0,
                "total_cost": 0
            }

        # Tarihe göre sırala
        txs = sorted(transactions, key=lambda x: x.date)
        
        remaining_quantity = 0.0
        realized_pnl = 0.0
        
        if method == "WAC":
            # Weighted Average Cost
            total_invested = 0.0
            
            for tx in txs:
                qty = float(tx.quantity)
                cost = float(tx.unit_price) * qty + float(tx.commission) + float(tx.tax)
                
                if tx.transaction_type == TransactionType.BUY:
                    total_invested += cost
                    remaining_quantity += qty
                elif tx.transaction_type == TransactionType.SELL:
                    if remaining_quantity > 0:
                        avg_cost_per_unit = total_invested / remaining_quantity
                        # Satış karı = (Satış geliri net) - (Satılan adet * ortalama maliyet)
                        net_revenue = (float(tx.unit_price) * qty) - (float(tx.commission) + float(tx.tax))
                        cost_of_sold = avg_cost_per_unit * qty
                        
                        realized_pnl += (net_revenue - cost_of_sold)
                        total_invested -= cost_of_sold
                        remaining_quantity -= qty
            
            average_cost = (total_invested / remaining_quantity) if remaining_quantity > 0 else 0.0
            
        elif method in ("FIFO", "LIFO"):
            # Queue for FIFO, Stack for LIFO
            inventory = deque() if method == "FIFO" else []
            
            for tx in txs:
                qty = float(tx.quantity)
                
                if tx.transaction_type == TransactionType.BUY:
                    # Birim başına tam maliyet
                    unit_full_cost = (float(tx.unit_price) * qty + float(tx.commission) + float(tx.tax)) / qty
                    inventory.append({"qty": qty, "unit_cost": unit_full_cost})
                    remaining_quantity += qty
                elif tx.transaction_type == TransactionType.SELL:
                    qty_to_sell = qty
                    net_revenue = (float(tx.unit_price) * qty) - (float(tx.commission) + float(tx.tax))
                    total_cost_of_sold = 0.0
                    
                    while qty_to_sell > 0 and inventory:
                        batch = inventory[0] if method == "FIFO" else inventory[-1]
                        
                        if batch["qty"] <= qty_to_sell:
                            total_cost_of_sold += batch["qty"] * batch["unit_cost"]
                            qty_to_sell -= batch["qty"]
                            if method == "FIFO":
                                inventory.popleft()
                            else:
                                inventory.pop()
                        else:
                            total_cost_of_sold += qty_to_sell * batch["unit_cost"]
                            batch["qty"] -= qty_to_sell
                            qty_to_sell = 0
                    
                    realized_pnl += (net_revenue - total_cost_of_sold)
                    remaining_quantity -= qty
            
            # Kalan envanterin ortalama maliyeti hesabı
            if remaining_quantity > 0:
                total_remaining_cost = sum(item["qty"] * item["unit_cost"] for item in inventory)
                average_cost = total_remaining_cost / remaining_quantity
            else:
                average_cost = 0.0
        else:
            raise ValueError(f"Bilinmeyen maliyet metodu: {method}")

        unrealized_pnl = 0.0
        if remaining_quantity > 0 and current_price > 0:
            unrealized_pnl = (current_price - average_cost) * remaining_quantity
            
        return {
            "remaining_quantity": remaining_quantity,
            "average_cost": average_cost,
            "realized_pnl": realized_pnl,
            "unrealized_pnl": unrealized_pnl,
            "total_cost": remaining_quantity * average_cost
        }

    @staticmethod
    def calculate_xirr(cash_flows: List[Tuple[datetime.date, float]]) -> float:
        """
        Para-ağırlıklı getiri (XIRR) hesaplar.
        cash_flows: (Tarih, Meblağ) listesi. 
        Meblağ: Alımlar eksi, Satışlar ve mevcut değer artı olarak girilmeli.
        """
        if not cash_flows or len(cash_flows) < 2:
            return 0.0
            
        cash_flows = sorted(cash_flows, key=lambda x: x[0])
        t0 = cash_flows[0][0]
        
        def xnpv(rate: float) -> float:
            if rate <= -1.0:
                return float('inf')
            res = 0.0
            for date, amount in cash_flows:
                days = (date - t0).days
                res += amount / ((1.0 + rate) ** (days / 365.0))
            return res

        # Newton-Raphson metodu
        guess = 0.1
        for _ in range(100):
            try:
                npv = xnpv(guess)
                if abs(npv) < 1e-5:
                    return guess
                
                # Derivasyon d(xnpv)/dx
                d_npv = 0.0
                for date, amount in cash_flows:
                    days = (date - t0).days
                    d_npv -= (days / 365.0) * amount / ((1.0 + guess) ** ((days / 365.0) + 1.0))
                
                if d_npv == 0:
                    break
                
                guess = guess - npv / d_npv
            except Exception:
                break
                
        return guess
