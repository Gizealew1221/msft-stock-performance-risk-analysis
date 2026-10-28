from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import yfinance as yf

plt.style.use("seaborn-v0_8-whitegrid")

ROOT = Path(__file__).resolve().parent
OUTPUT_DIR = ROOT / "outputs"
OUTPUT_DIR.mkdir(exist_ok=True)


def fetch_prices() -> pd.DataFrame:
    tickers = ["MSFT", "^GSPC"]
    data = yf.download(
        tickers,
        period="3y",
        interval="1d",
        auto_adjust=True,
        progress=False,
    )

    if data.empty:
        raise ValueError("No data downloaded. Check your internet connection.")

    prices = data["Close"].copy()
    prices = prices.rename(columns={"MSFT": "Microsoft", "^GSPC": "SP500"})
    prices.index = pd.to_datetime(prices.index)

    if prices.index.tz is not None:
        prices.index = prices.index.tz_localize(None)

    prices = prices.sort_index()
    prices = prices[~prices.index.duplicated(keep="first")]
    prices = prices.dropna()

    assert not prices.empty, "The dataset is empty."
    assert not prices.index.duplicated().any(), "Duplicate dates found."
    assert (prices > 0).all().all(), "Nonpositive prices found."

    return prices


def save_outputs(prices: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    daily_returns = prices.pct_change(fill_method=None).dropna()
    cumulative_returns = (1 + daily_returns).cumprod() - 1
    wealth_index = (1 + daily_returns).cumprod()
    running_peak = wealth_index.cummax()
    drawdown = (wealth_index / running_peak) - 1
    max_drawdown = drawdown.min()
    annualized_volatility = daily_returns.std() * np.sqrt(252)
    annualized_mean_return = daily_returns.mean() * 252
    sharpe_ratio = annualized_mean_return / annualized_volatility
    years = (daily_returns.index[-1] - daily_returns.index[0]).days / 365.25
    annualized_cagr = (1 + cumulative_returns.iloc[-1]) ** (1 / years) - 1

    performance_summary = pd.DataFrame(
        {
            "Cumulative Return (%)": cumulative_returns.iloc[-1] * 100,
            "Annualized CAGR (%)": annualized_cagr * 100,
            "Annualized Volatility (%)": annualized_volatility * 100,
            "Sharpe Ratio (0% risk-free)": sharpe_ratio,
            "Maximum Drawdown (%)": max_drawdown * 100,
        }
    ).round(2)

    cumulative_plot = OUTPUT_DIR / "cumulative_returns.png"
    fig, ax = plt.subplots(figsize=(12, 6))
    for column in cumulative_returns.columns:
        ax.plot(cumulative_returns.index, cumulative_returns[column] * 100, label=column)
    ax.set_title("Cumulative Returns: Microsoft vs S&P 500")
    ax.set_xlabel("Date")
    ax.set_ylabel("Cumulative Return (%)")
    ax.legend()
    fig.tight_layout()
    fig.savefig(cumulative_plot)
    plt.close(fig)

    drawdown_plot = OUTPUT_DIR / "drawdown.png"
    fig, ax = plt.subplots(figsize=(12, 6))
    for column in drawdown.columns:
        ax.plot(drawdown.index, drawdown[column] * 100, label=column)
    ax.set_title("Historical Drawdown: Microsoft vs S&P 500")
    ax.set_xlabel("Date")
    ax.set_ylabel("Drawdown (%)")
    ax.legend()
    fig.tight_layout()
    fig.savefig(drawdown_plot)
    plt.close(fig)

    performance_summary.to_csv(ROOT / "msft_performance_summary.csv")
    daily_returns.to_csv(ROOT / "msft_daily_returns.csv")

    return daily_returns, cumulative_returns, performance_summary


def main() -> None:
    prices = fetch_prices()
    daily_returns, cumulative_returns, performance_summary = save_outputs(prices)
    print("Data validation passed.")
    print("Observations available:", len(prices))
    print("Start date:", prices.index.min().date())
    print("End date:", prices.index.max().date())
    print("\nPerformance summary:")
    print(performance_summary)
    print("\nGenerated files:")
    print("- msft_performance_summary.csv")
    print("- msft_daily_returns.csv")
    print("- outputs/cumulative_returns.png")
    print("- outputs/drawdown.png")


if __name__ == "__main__":
    main()
