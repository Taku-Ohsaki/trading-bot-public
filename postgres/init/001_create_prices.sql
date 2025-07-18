DROP TABLE IF EXISTS prices;
CREATE TABLE prices(
  date DATE NOT NULL,
  symbol TEXT NOT NULL,
  open NUMERIC,
  high NUMERIC,
  low NUMERIC,
  close NUMERIC,
  volume BIGINT,
  PRIMARY KEY (date, symbol)
);