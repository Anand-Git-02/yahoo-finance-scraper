import streamlit as st
import pandas as pd
import numpy as np
import time
from io import BytesIO
from main import YahooFinanceScraper

# Page Configuration
st.set_page_config(
    page_title="Yahoo Finance Scraper",
    page_icon="📈",
    layout="wide"
)

def clean_data(data):
    """
    Cleans and transforms raw scraped data into a structured integer/float DataFrame.
    """
    if not data:
        return pd.DataFrame()

    df = pd.DataFrame(data)
    
    # Apply user-defined cleaning logic
    cleaned_df = (
        df
        .apply(lambda col: col.str.strip() if col.dtype == "object" else col)
        .assign(
            price=lambda df_: pd.to_numeric(df_["price"].astype(str).str.replace(",", "", regex=False), errors="coerce"),
            change=lambda df_: pd.to_numeric(
                df_["change"].astype(str).str.replace("+", "", regex=False).str.replace(",", "", regex=False),
                errors="coerce"
            ),
            volume=lambda df_: pd.to_numeric(
                df_["volume"].astype(str)
                .str.replace(",", "", regex=False)
                .str.replace("M", "", regex=False),
                errors="coerce"
            ),
            market_cap=lambda df_: df_["market_cap"].apply(
                lambda v: (
                    float(str(v).replace("T", "").replace(",", "")) * 1000
                    if "T" in str(v)
                    else float(str(v).replace("B", "").replace(",", ""))
                ) if isinstance(v, str) and v and v != "N/A" else np.nan
            ),
            pe_ratio=lambda df_: pd.to_numeric(
                df_["pe_ratio"].astype(str).replace("-", np.nan).str.replace(",", "", regex=False),
                errors="coerce"
            )
        )
        .rename(columns={
            "price": "Price (USD)",
            "change": "Change",
            "volume": "Volume (M)",
            "market_cap": "Market Cap (B)",
            "pe_ratio": "PE Ratio"
        })
    )
    
    return cleaned_df

def convert_df_to_csv(df):
    """Converts DataFrame to CSV for download."""
    return df.to_csv(index=False).encode('utf-8')

def convert_df_to_excel(df):
    """Converts DataFrame to Excel for download."""
    output = BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        df.to_excel(writer, index=False, sheet_name='Sheet1')
    processed_data = output.getvalue()
    return processed_data

# App Logic
st.title("📈 Yahoo Finance Most Active Stocks Scraper")
st.write("Click the button below to scrape the latest 'Most Active' stocks data from Yahoo Finance.")

if st.button("🚀 Scrape Data"):
    with st.spinner("Initializing Scraper... Please wait (this make take a few minutes)..."):
        try:
            # Initialize Scraper
            # Headless mode is required for Streamlit Cloud
            scraper = YahooFinanceScraper(headless=True)
            
            # Progress bar placeholder
            progress_bar = st.progress(0)
            status_text = st.empty()
            
            status_text.text("Navigating to Yahoo Finance...")
            
            # We need to modify the run method or just use the public methods to update progress
            raw_data = []
            for page, total, data_snapshot in scraper.run():
                raw_data = data_snapshot
                status_text.text(f"Scraping page {page}... Collected {total} rows.")
                # Simple progress update: increase by 10% per page, loop back or cap at 90%
                progress = min(page * 10, 90)
                progress_bar.progress(progress)
            
            progress_bar.progress(100)
            status_text.text("Scraping Completed!")
            
            if raw_data:
                st.success(f"Successfully scraped {len(raw_data)} rows!")
                
                # Cleanup
                clean_df = clean_data(raw_data)
                
                # Display Data
                st.dataframe(clean_df, use_container_width=True)
                
                # Download Columns
                col1, col2 = st.columns(2)
                
                with col1:
                    csv = convert_df_to_csv(clean_df)
                    st.download_button(
                        label="📥 Download as CSV",
                        data=csv,
                        file_name='yahoo_finance_most_active.csv',
                        mime='text/csv',
                    )
                
                with col2:
                    excel = convert_df_to_excel(clean_df)
                    st.download_button(
                        label="📥 Download as Excel",
                        data=excel,
                        file_name='yahoo_finance_most_active.xlsx',
                        mime='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
                    )
            else:
                st.warning("No data was returned. It's possible the layout changed or scraping was blocked.")
                
        except Exception as e:
            st.error(f"An error occurred: {e}")
