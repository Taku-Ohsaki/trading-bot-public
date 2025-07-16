CREATE TABLE IF NOT EXISTS ticks (
  trade_time TIMESTAMPTZ NOT NULL,
  symbol     TEXT        NOT NULL,
  price      NUMERIC     NOT NULL,
  volume     BIGINT      NOT NULL,
  PRIMARY KEY (trade_time, symbol)
);
