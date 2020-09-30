import datetime as dt
from typing import Sequence, Union

import pandas as pd

from . import utils
from .constants import FINANCIAL_STATEMENTS_TYPE, INDUSTRY_LEVEL
from .DBInterface import DBInterface
from .TradingCalendar import TradingCalendar


class Factor(object):
    """
    Factor base class
    """

    def __init__(self, db_interface: DBInterface, table_name: str, factor_names: Union[str, Sequence[str]]):
        super().__init__()
        self.db_interface = db_interface
        self._check_args(table_name, factor_names)

        self.table_name = table_name
        self.factor_names = factor_names
        self.calendar = TradingCalendar(db_interface)

    def get_data(self, kwargs):
        raise NotImplementedError()

    # helper functions
    def _check_args(self, table_name: str, factor_names: Union[str, Sequence[str]]):
        table_name = table_name.lower()
        assert self.db_interface.exist_table(table_name), f'数据库中不存在表 {table_name}'

        if factor_names:
            columns = self.db_interface.get_columns_names(table_name)
            if isinstance(factor_names, str):
                assert factor_names in columns, f'表 {table_name} 中不存在 {factor_names} 列'
            else:
                for name in factor_names:
                    assert name in columns, f'表 {table_name} 中不存在 {name} 列'


class NonFinancialFactor(Factor):
    """
    非财报数据
    """

    def __init__(self, db_interface: DBInterface, table_name: str, factor_names: Union[str, Sequence[str]]):
        super().__init__(db_interface, table_name, factor_names)
        assert not any([it in table_name for it in FINANCIAL_STATEMENTS_TYPE]), \
            f'{table_name} 为财报数据, 请使用 FinancialFactor 类!'

    def get_data(self, kwargs):
        raise NotImplementedError()


class CompactFactor(NonFinancialFactor):
    """
    Compact Factors

    数字变动很不平常的特性, 列如复权因子, 行业, 股本 等. 对于的数据库表格为: {'DateTime', 'ID', 'FactorName'}
    该类可以缓存以提升效率
    """

    def __init__(self, db_interface: DBInterface, factor_name: str):
        super().__init__(db_interface, factor_name, factor_name)
        self.data = db_interface.read_table(factor_name)

    def get_data(self, dates: Sequence[dt.datetime] = None,
                 start_date: utils.DateType = None, end_date: utils.DateType = None,
                 ids: Union[Sequence[str], str] = None) -> pd.DataFrame:
        """
        :param start_date: start date
        :param end_date: end date
        :param dates: selected dates
        :param ids: query stocks
        :return: pandas.DataFrame with DateTime as index and stock as column
        """
        data = self.data.copy()
        if ids:
            data = data.loc[(slice(None), ids)]
        if dates:
            end_date = max(dates)
        if not end_date:
            end_date = dt.datetime.today()
        date_list = self.calendar.select_dates(end_date=end_date)
        df = data.unstack().reindex(date_list).ffill()
        if start_date:
            start_date = utils.date_type2datetime(start_date)
            df = df.loc[df.index >= start_date, :]
        if dates:
            df = df.loc[dates, :]
        return df


class IndustryFactor(CompactFactor):
    """
    股票行业分类
    """

    def __init__(self, db_interface: DBInterface, provider: str, level: int) -> None:
        """

        :param db_interface: DB Interface
        :param provider: Industry classification data provider
        :param level: Level of industry classification
        """
        assert 0 < level <= INDUSTRY_LEVEL[provider], f'{provider}行业没有{level}级'
        table_name = f'{provider}行业'
        super().__init__(db_interface, table_name)

        if level != INDUSTRY_LEVEL[provider]:
            translation = utils.load_param('industry.json')
            new_translation = {}
            for key, value in translation[table_name].items():
                new_translation[key] = value[f'level_{level}']

            self.data = self.data.map(new_translation)


class ContinuousFactor(NonFinancialFactor):
    """
    Continuous Factors
    """

    def __init__(self, db_interface: DBInterface, table_name: str, factor_names: Union[str, Sequence[str]]):
        super().__init__(db_interface, table_name, factor_names)

    def get_data(self, dates: Sequence[dt.datetime] = None,
                 start_date: utils.DateType = None, end_date: utils.DateType = None,
                 ids: Sequence[str] = None, unstack: bool = True) -> Union[pd.Series, pd.DataFrame]:
        """
        :param start_date: start date
        :param end_date: end date
        :param dates: selected dates
        :param ids: query stocks
        :param unstack: if unstack data from long to wide
        :return: pandas.DataFrame with DateTime as index and stock as column
        """

        df = self.db_interface.read_table(self.table_name, columns=self.factor_names, start_date=start_date,
                                          end_date=end_date,
                                          dates=dates, ids=ids)
        if not isinstance(self.factor_names, str):
            df.columns = self.factor_names
            return df

        if isinstance(df.index, pd.MultiIndex) & unstack:
            df = df.unstack()
        return df


class FinancialFactor(Factor):
    """
    财报数据
    """

    def __init__(self, db_interface: DBInterface, table_name: str, factor_names: Union[str, Sequence[str]]):
        super().__init__(db_interface, table_name, factor_names)
        assert any([it in table_name for it in FINANCIAL_STATEMENTS_TYPE]), f'{table_name} 非财报数据!'

    def get_data(self, kwargs):
        raise NotImplementedError()


class YearlyReportFinancialFactor(FinancialFactor):
    """
    年报数据
    """

    def __init__(self, db_interface: DBInterface, table_name: str, factor_names: Union[str, Sequence[str]]):
        super().__init__(db_interface, table_name, factor_names)

    def get_data(self, dates: Sequence[dt.datetime] = None,
                 start_date: utils.DateType = None, end_date: utils.DateType = None,
                 ids: Sequence[str] = None) -> Union[pd.Series, pd.DataFrame]:
        """
        :param start_date: start date
        :param end_date: end date
        :param dates: selected dates
        :param ids: query stocks
        :return: pandas.DataFrame with DateTime as index and stock as column
        """
        buffer = dt.timedelta(days=365 * 2)
        if dates:
            start_date = min(dates)
            end_date = max(end_date)
        else:
            start_date = utils.date_type2datetime(start_date)
            end_date = utils.date_type2datetime(end_date)
        buffer_start = start_date - buffer

        data = self.db_interface.read_table(self.table_name, self.factor_names, start_date=buffer_start,
                                            end_date=end_date, ids=ids).dropna()
        data = data.loc[data.index.get_level_values('报告期').month == 12, :]

        if dates:
            index_dates = sorted(list(set(dates) & set(data.index.get_level_values('DateTime'))))
        else:
            index_dates = self.calendar.select_dates(buffer_start, end_date)
            dates = self.calendar.select_dates(start_date, end_date)

        df = data.droplevel('报告期').unstack().reindex(index_dates).ffill().reindex(dates)
        return df


class TTMFinancialFactor(FinancialFactor):
    def __init__(self, db_interface: DBInterface, table_name: str, factor_names: Union[str, Sequence[str]]):
        super().__init__(db_interface, table_name, factor_names)

    def get_data(self, dates: Sequence[dt.datetime] = None,
                 start_date: utils.DateType = None, end_date: utils.DateType = None,
                 ids: Sequence[str] = None, unstack: bool = True) -> Union[pd.Series, pd.DataFrame]:
        """
        :param start_date: start date
        :param end_date: end date
        :param dates: selected dates
        :param ids: query stocks
        :param unstack: if unstack data from long to wide
        :return: pandas.DataFrame with DateTime as index and stock as column
        """
        pass


class LatestFinancialFactor(FinancialFactor):
    def __init__(self, db_interface: DBInterface, table_name: str, factor_names: Union[str, Sequence[str]]):
        super().__init__(db_interface, table_name, factor_names)

    def get_data(self, dates: Sequence[dt.datetime] = None,
                 start_date: utils.DateType = None, end_date: utils.DateType = None,
                 ids: Sequence[str] = None, unstack: bool = True) -> Union[pd.Series, pd.DataFrame]:
        """
        :param start_date: start date
        :param end_date: end date
        :param dates: selected dates
        :param ids: query stocks
        :param unstack: if unstack data from long to wide
        :return: pandas.DataFrame with DateTime as index and stock as column
        """
        pass