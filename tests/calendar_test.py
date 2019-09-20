import datetime as dt
import unittest

from AShareData.DBInterface import MySQLInterface, prepare_engine
from AShareData.TradingCalendar import TradingCalendar


class MyTestCase(unittest.TestCase):
    def setUp(self) -> None:
        config_loc = 'config.json'
        engine = prepare_engine(config_loc)
        self.calendar = TradingCalendar(MySQLInterface(engine))

    def test_days_count(self):
        start = dt.datetime(2019, 1, 4)
        end = dt.datetime(2019, 1, 7)
        self.assertEqual(self.calendar.days_count(start, end), 1)
        self.assertEqual(self.calendar.days_count(end, start), -1)
        self.assertEqual(self.calendar.days_count(start, start), 0)

    def test_first_day_of_month(self):
        start = dt.datetime(2019, 3, 2)
        end = dt.datetime(2019, 4, 2)
        self.assertEqual(self.calendar.first_day_of_month(start, end)[0], dt.datetime(2019, 4, 1))

    def test_last_day_of_month(self):
        start = dt.datetime(2019, 3, 2)
        end = dt.datetime(2019, 4, 2)
        self.assertEqual(self.calendar.last_day_of_month(start, end)[0], dt.datetime(2019, 3, 29))

    def test_last_day_of_year(self):
        start = dt.datetime(2018, 3, 2)
        end = dt.datetime(2019, 4, 2)
        self.assertEqual(self.calendar.last_day_of_year(start, end)[0], dt.datetime(2018, 12, 28))

    def test_select_dates(self):
        start = dt.datetime(2019, 9, 2)
        end = dt.datetime(2019, 9, 3)
        self.assertEqual(self.calendar.select_dates(start, end), [start, end])


if __name__ == '__main__':
    unittest.main()