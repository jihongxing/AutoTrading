"""
BTC 自动交易系统 — 费用计算器
"""

from src.common.logging import get_logger
from src.user.models import PLAN_CONFIG, SubscriptionPlan

logger = get_logger(__name__)


class FeeCalculator:
    """
    费用计算器
    
    根据订阅计划计算平台费用。
    """
    
    def __init__(self):
        pass
    
    def get_fee_rate(self, plan: SubscriptionPlan) -> float:
        """
        获取费率
        
        Args:
            plan: 订阅计划
        
        Returns:
            费率（0-1）
        """
        return PLAN_CONFIG[plan]["fee_rate"]
    
    def calculate_platform_fee(
        self,
        profit: float,
        fee_rate: float,
    ) -> float:
        """
        计算平台费用
        
        仅对盈利部分收费。
        
        Args:
            profit: 盈利金额
            fee_rate: 费率
        
        Returns:
            平台费用
        """
        if profit <= 0:
            return 0.0
        
        return profit * fee_rate
    
    def calculate_user_net(
        self,
        profit: float,
        fee_rate: float,
    ) -> float:
        """
        计算用户净收益
        
        Args:
            profit: 盈利金额
            fee_rate: 费率
        
        Returns:
            用户净收益
        """
        if profit <= 0:
            return profit  # 亏损不收费
        
        platform_fee = self.calculate_platform_fee(profit, fee_rate)
        return profit - platform_fee
    
    def get_monthly_subscription(self, plan: SubscriptionPlan) -> float:
        """获取月订阅费"""
        return PLAN_CONFIG[plan]["monthly_price"]
    
    def estimate_fees(
        self,
        expected_profit: float,
        plan: SubscriptionPlan,
    ) -> dict[str, float]:
        """
        估算费用
        
        Args:
            expected_profit: 预期盈利
            plan: 订阅计划
        
        Returns:
            费用明细
        """
        fee_rate = self.get_fee_rate(plan)
        platform_fee = self.calculate_platform_fee(expected_profit, fee_rate)
        monthly_sub = self.get_monthly_subscription(plan)
        
        return {
            "expected_profit": expected_profit,
            "fee_rate": fee_rate,
            "platform_fee": platform_fee,
            "monthly_subscription": monthly_sub,
            "total_fees": platform_fee + monthly_sub,
            "user_net": expected_profit - platform_fee - monthly_sub,
        }
