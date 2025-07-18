-- イントラデイ価格テーブル（1分足データ用）
-- 仕様書に従い、PRIMARY KEY は (datetime, symbol) 形式
DROP TABLE IF EXISTS intraday_prices;
CREATE TABLE intraday_prices(
  datetime TIMESTAMP NOT NULL,
  symbol TEXT NOT NULL,
  open NUMERIC,
  high NUMERIC,
  low NUMERIC,
  close NUMERIC,
  volume BIGINT,
  PRIMARY KEY (datetime, symbol)
);

-- インデックス作成（時系列データに最適化）
CREATE INDEX idx_intraday_datetime ON intraday_prices(datetime);
CREATE INDEX idx_intraday_symbol ON intraday_prices(symbol);
CREATE INDEX idx_intraday_datetime_symbol ON intraday_prices(datetime, symbol);