import datetime as dt
import sys

from AShareData.AShareDataReader import AShareDataReader
from AShareData.config import set_global_config
from AShareData.FactorCompositor import FactorPortfolio, FactorPortfolioPolicy
from AShareData.utils import StockSelectionPolicy

if __name__ == '__main__':
    set_global_config(sys.argv[1])

    data_reader = AShareDataReader()
    stock_selection_policy = StockSelectionPolicy()
    stock_selection_policy.ignore_new_stock_period = 360
    stock_selection_policy.ignore_st = True
    stock_selection_policy.ignore_pause = True

    policy = FactorPortfolioPolicy()
    policy.bins = [5, 10]
    policy.stock_selection_policy = stock_selection_policy
    policy.start_date = dt.datetime(2010, 1, 1)
    policy.industry = data_reader.industry('申万', 1)
    policy.weight = data_reader.stock_free_floating_market_cap

    policy.name = data_reader.beta.factor_name
    policy.factor = data_reader.beta

    sub_port = FactorPortfolio(factor_portfolio_policy=policy)
    sub_port.update()
