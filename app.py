import streamlit as st
from analyzer import analyze_stock, export_to_excel
import os
import pandas as pd
from datetime import date
from vnstock import Vnstock
import plotly.graph_objects as go
import plotly.express as px
import matplotlib.pyplot as plt
import seaborn as sns
from concurrent.futures import ThreadPoolExecutor


st.set_page_config(page_title='Phân Tích Cổ Phiếu', layout='wide')
tab2, tab3, tab4, tab5, tab6, tab7 = st.tabs([
    '🏭 Dòng Tiền Theo Nhóm Ngành',
    '📝 Nhập Mã Tùy Chọn',
    '📊 Phân Tích Cơ Bản',
    '📉 Biểu Đồ Giá',
    '📈 Cập nhật Giá Cổ Phiếu Realtime',
    '💧 Phân Tích Dòng Tiền Theo Phút'
])


# ==== TAB 2 ====
with tab2:
    st.title('🏭 Theo Dõi Dòng Tiền Theo Nhóm Ngành')

    sector_map = {
        'Ngân hàng': ['VCB', 'CTG', 'BID', 'TCB', 'MBB', 'ACB', 'HDB', 'LPB', 'SHB', 'STB'],
        'Chứng khoán': ['SSI', 'VND', 'HCM', 'VCI', 'FTS', 'CTS', 'MBS', 'SHS', 'BSI', 'VIX'],
        'Thép': ['HPG', 'HSG', 'NKG', 'TLH'],
        'Bất động sản': ['VIC', 'VHM', 'NLG', 'KDH', 'DXG', 'HDG', 'LDG', 'HDC', 'NVL', 'LHG'],
        'Công nghệ': ['FPT', 'CMG', 'CTR', 'VGI'],
        'Bán lẻ': ['MSN', 'MWG', 'DGW', 'PNJ', 'FRT'],
        'Điện nước': ['BWE', 'NT2', 'POW', 'PC1', 'DQC'],
        'Dầu khí': ['PVS', 'PVD', 'GAS', 'PLX', 'BSR'],
        'Xây dựng': ['CTD', 'HBC', 'CII', 'VCG', 'FCN'],
        'Đầu tư công': ['HHV', 'LCG', 'HTI', 'DPG', 'EVG'],
        'Thực phẩm': ['DBC', 'QNS', 'NAF', 'SBT', 'MCH', 'VNM', 'SAB'],
        'Bảo hiểm': ['BVH', 'BMI', 'MIG', 'BIC', 'PVI'],
        'Thủy sản': ['VHC', 'ANV', 'FMC', 'ASM'],
        'Dệt may': ['MSH', 'TCM', 'TNG', 'VGT', 'STK'],
        'Cao su': ['GVR', 'DPR', 'HRC', 'PHR'],
        'Dược phẩm': ['DCL', 'DHG', 'IMP', 'TRA', 'DVN'],
        'Vận tải': ['PVT', 'HAH', 'GMD', 'VNS', 'VSC'],
        'Nhựa': ['AAA', 'BMP', 'NTP', 'DNP'],
        'Khu CN': ['KBC', 'SZC', 'TIP', 'BCM', 'VGC', 'IDC'],
        'Phân bón': ['DGC', 'DPM', 'DCM', 'BFC', 'LAS']
    }

    selected_date = st.date_input('Chọn ngày giao dịch:', value=date.today(), key='date_sector')
    selected_sector = st.selectbox('Chọn nhóm ngành:', options=list(sector_map.keys()))
    analyze_button = st.button('🔍 Phân Tích Nhóm Ngành', key='analyze_sector')

    def process_symbol(symbol, selected_date):
        try:
            # Khởi tạo đối tượng lấy dữ liệu intraday
            stock = Vnstock().stock(symbol=symbol, source='VCI')
            df_intraday = stock.quote.intraday(symbol=symbol, page_size=10000)

            if df_intraday is None or df_intraday.empty:
                st.warning(f"Không có dữ liệu intraday cho mã {symbol}.")
                return None

            # Chuyển đổi dữ liệu về dạng thời gian
            df_intraday['time'] = pd.to_datetime(df_intraday['time'])
            df_intraday.set_index('time', inplace=True)

            # Gộp theo từng phút
            df_intraday['minute'] = df_intraday.index.floor('T')  # 'T' là viết tắt cho 'minutely'

            # Tính volume mua & bán
            df_intraday['volume_buy'] = df_intraday.apply(lambda x: x['volume'] if x['match_type'] == 'Buy' else 0, axis=1)
            df_intraday['volume_sell'] = df_intraday.apply(lambda x: x['volume'] if x['match_type'] == 'Sell' else 0, axis=1)

            # Nhóm theo từng phút
            df_min = df_intraday.groupby('minute').agg(
                volume_buy=('volume_buy', 'sum'),
                volume_sell=('volume_sell', 'sum'),
                avg_price=('price', 'mean')
            ).reset_index()

            # Tính dòng tiền (Value = Giá * Volume)
            df_min['value_buy'] = df_min['volume_buy'] * df_min['avg_price'] * 1000
            df_min['value_sell'] = df_min['volume_sell'] * df_min['avg_price'] * 1000
            df_min['net'] = df_min['volume_buy'] - df_min['volume_sell']
            df_min['net_value'] = df_min['value_buy'] - df_min['value_sell']

            # Tính khối lượng mua/bán lũy kế
            df_min['cumulative_value_buy'] = df_min['value_buy'].cumsum()
            df_min['cumulative_value_sell'] = df_min['value_sell'].cumsum()
            df_min['cumulative_value_net'] = df_min['net_value'].cumsum()

            # Tính dòng tiền lũy kế
            df_min['cumulative_net'] = df_min['cumulative_value_buy'] - df_min['cumulative_value_sell']

            # Lấy các dòng tiền lũy kế cuối cùng
            cumulative_buy = df_min['cumulative_value_buy'].iloc[-1] if not df_min.empty else 0
            cumulative_sell = df_min['cumulative_value_sell'].iloc[-1] if not df_min.empty else 0
            cumulative_net = df_min['cumulative_net'].iloc[-1] if not df_min.empty else 0

            return {
                "symbol": symbol,
                "cumulative_value_buy": cumulative_buy,
                "cumulative_value_sell": cumulative_sell,
                "cumulative_value_net": cumulative_net
            }
        except Exception:
            return None

    if analyze_button and selected_sector:
        symbols = sector_map[selected_sector]
        st.info(f"Đang phân tích {len(symbols)} mã trong nhóm '{selected_sector}'...")

        with st.spinner("Đang xử lý..."):
            with ThreadPoolExecutor(max_workers=6) as executor:
                futures = [executor.submit(process_symbol, sym, selected_date) for sym in symbols]
                results = [f.result() for f in futures if f.result() is not None]

        if results:
            df_sector = pd.DataFrame(results)
            # Tạo bản hiển thị đã định dạng số kiểu 1.000.000
            df_display = df_sector.copy()
            for col in ['cumulative_value_buy', 'cumulative_value_sell', 'cumulative_value_net']:
                df_display[col] = df_display[col].map(lambda x: f"{x:,.0f}".replace(",", "."))

            # Hiển thị bảng định dạng
            st.subheader("📋 Bảng Dòng Tiền Mua/Bán/Ròng Lũy Kế (VND)")
            st.dataframe(df_display, use_container_width=True)

            import altair as alt         
            
            st.subheader(f'📊 Biểu Đồ Dòng Tiền lũy kế Nhóm: {selected_sector}')

            # Dữ liệu dạng long cho biểu đồ cột
            df_melted = df_sector.melt(id_vars="symbol", value_vars=["cumulative_value_buy", "cumulative_value_sell"], var_name="type", value_name="value")

            bars = alt.Chart(df_melted).mark_bar().encode(
                x=alt.X('symbol:N', title='Mã cổ phiếu'),
                xOffset='type:N',
                y=alt.Y('value:Q', title='VND'),
                color=alt.Color('type:N', scale=alt.Scale(domain=['cumulative_value_buy', 'cumulative_value_sell'], range=['#2E86AB', '#E74C3C'])),
                tooltip=['symbol', 'type', alt.Tooltip('value:Q', format=',')]
            ).properties(
                width=700,
                height=400
            )

            line = alt.Chart(df_sector).mark_line(color='purple', strokeWidth=3).encode(
                x=alt.X('symbol:N', title='Mã cổ phiếu'),
                y=alt.Y('cumulative_value_net:Q', title='VND'),
                tooltip=['symbol', alt.Tooltip('cumulative_value_net:Q', format=',')]
            )

            chart = (bars + line).properties(
                width=700,
                height=400
            ).resolve_scale(
                y='shared'
            )

            st.altair_chart(chart, use_container_width=True)
        else:
            st.warning("Không thể phân tích dòng tiền nhóm ngành này.")



# ==== TAB 3 ====
with tab3:
    # Define the function for processing stock data
    def process_symbol(symbol, selected_date):
        try:
            # Khởi tạo đối tượng lấy dữ liệu intraday
            stock = Vnstock().stock(symbol=symbol, source='VCI')
            df_intraday = stock.quote.intraday(symbol=symbol, page_size=10000)

            if df_intraday is None or df_intraday.empty:
                st.warning(f"Không có dữ liệu intraday cho mã {symbol}.")
                return None

            # Chuyển đổi dữ liệu về dạng thời gian
            df_intraday['time'] = pd.to_datetime(df_intraday['time'])
            df_intraday.set_index('time', inplace=True)

            # Gộp theo từng phút
            df_intraday['minute'] = df_intraday.index.floor('T')

            # Tính volume mua & bán
            df_intraday['volume_buy'] = df_intraday.apply(lambda x: x['volume'] if x['match_type'] == 'Buy' else 0, axis=1)
            df_intraday['volume_sell'] = df_intraday.apply(lambda x: x['volume'] if x['match_type'] == 'Sell' else 0, axis=1)

            # Nhóm theo từng phút
            df_min = df_intraday.groupby('minute').agg(
                volume_buy=('volume_buy', 'sum'),
                volume_sell=('volume_sell', 'sum'),
                avg_price=('price', 'mean')
            ).reset_index()

            # Tính dòng tiền (Value = Giá * Volume)
            df_min['value_buy'] = df_min['volume_buy'] * df_min['avg_price'] * 1000
            df_min['value_sell'] = df_min['volume_sell'] * df_min['avg_price'] * 1000
            df_min['net'] = df_min['volume_buy'] - df_min['volume_sell']
            df_min['net_value'] = df_min['value_buy'] - df_min['value_sell']

            # Tính khối lượng mua/bán lũy kế
            df_min['cumulative_value_buy'] = df_min['value_buy'].cumsum()
            df_min['cumulative_value_sell'] = df_min['value_sell'].cumsum()
            df_min['cumulative_value_net'] = df_min['net_value'].cumsum()

            # Tính dòng tiền lũy kế
            df_min['cumulative_net'] = df_min['cumulative_value_buy'] - df_min['cumulative_value_sell']

            # Lấy các dòng tiền lũy kế cuối cùng
            cumulative_buy = df_min['cumulative_value_buy'].iloc[-1] if not df_min.empty else 0
            cumulative_sell = df_min['cumulative_value_sell'].iloc[-1] if not df_min.empty else 0
            cumulative_net = df_min['cumulative_net'].iloc[-1] if not df_min.empty else 0

            return {
                "symbol": symbol,
                "cumulative_value_buy": cumulative_buy,
                "cumulative_value_sell": cumulative_sell,
                "cumulative_value_net": cumulative_net
            }
        except Exception:
            return None

    # Main Streamlit code
    st.title('📊 Phân Tích Dòng Tiền Cổ Phiếu')

    # Option 1: Upload CSV file with stock symbols
    uploaded_file = st.file_uploader("Tải lên file CSV chứa mã cổ phiếu", type="csv")

    # Option 2: Manual input of stock symbols
    manual_input = st.text_input("Nhập mã cổ phiếu (cách nhau bằng dấu phẩy):", "")

    # Option 3: Select sector (optional)
    sector_map = {
        'Ngân hàng': ['VCB', 'CTG', 'BID', 'TCB', 'MBB', 'ACB', 'HDB', 'LPB', 'SHB', 'STB'],
        'Chứng khoán': ['SSI', 'VND', 'HCM', 'VCI', 'FTS', 'CTS', 'MBS', 'SHS', 'BSI', 'VIX'],
        'Ngân hàng': ['VCB', 'CTG', 'BID', 'TCB', 'MBB', 'ACB', 'HDB', 'LPB', 'SHB', 'STB'],
        'Chứng khoán': ['SSI', 'VND', 'HCM', 'VCI', 'FTS', 'CTS', 'MBS', 'SHS', 'BSI', 'VIX'],
        'Thép': ['HPG', 'HSG', 'NKG', 'TLH'],
        'Bất động sản': ['VIC', 'VHM', 'NLG', 'KDH', 'DXG', 'HDG', 'LDG', 'HDC', 'NVL', 'LHG'],
        'Công nghệ': ['FPT', 'CMG', 'CTR', 'VGI'],
        'Bán lẻ': ['MSN', 'MWG', 'DGW', 'PNJ', 'FRT'],
        'Điện nước': ['BWE', 'NT2', 'POW', 'PC1', 'DQC'],
        'Dầu khí': ['PVS', 'PVD', 'GAS', 'PLX', 'BSR'],
        'Xây dựng': ['CTD', 'HBC', 'CII', 'VCG', 'FCN'],
        'Đầu tư công': ['HHV', 'LCG', 'HTI', 'DPG', 'EVG'],
        'Thực phẩm': ['DBC', 'QNS', 'NAF', 'SBT', 'MCH', 'VNM', 'SAB'],
        'Bảo hiểm': ['BVH', 'BMI', 'MIG', 'BIC', 'PVI'],
        'Thủy sản': ['VHC', 'ANV', 'FMC', 'ASM'],
        'Dệt may': ['MSH', 'TCM', 'TNG', 'VGT', 'STK'],
        'Cao su': ['GVR', 'DPR', 'HRC', 'PHR'],
        'Dược phẩm': ['DCL', 'DHG', 'IMP', 'TRA', 'DVN'],
        'Vận tải': ['PVT', 'HAH', 'GMD', 'VNS', 'VSC'],
        'Nhựa': ['AAA', 'BMP', 'NTP', 'DNP'],
        'Khu CN': ['KBC', 'SZC', 'TIP', 'BCM', 'VGC', 'IDC'],
        'Phân bón': ['DGC', 'DPM', 'DCM', 'BFC', 'LAS']
        # Add other sectors as required...
    }

    selected_sector = st.selectbox('Chọn nhóm ngành:', options=list(sector_map.keys()), index=0, key="sector_select")

    # Select a date for analysis
    selected_date = st.date_input('Chọn ngày giao dịch:', value=date.today(), key='date')

    # Define button to trigger analysis
    analyze_button = st.button('🔍 Phân Tích Dòng Tiền')

    # Process the symbols based on the input
    if analyze_button:
        st.info(f"Đang phân tích các mã cổ phiếu...")

        if uploaded_file is not None:
            # Read CSV file and extract stock symbols
            df_csv = pd.read_csv(uploaded_file)
            symbols = df_csv['symbol'].dropna().tolist()  # Assuming the CSV has a column 'symbol'
        elif manual_input:
            # Process manual input
            symbols = [sym.strip() for sym in manual_input.split(',')]
        elif selected_sector:
            # Default to selected sector symbols if no CSV or manual input
            symbols = sector_map.get(selected_sector, [])
        else:
            st.warning("Vui lòng nhập mã cổ phiếu hoặc chọn nhóm ngành.")
            symbols = []

        if symbols:
            with st.spinner("Đang xử lý..."):
                with ThreadPoolExecutor(max_workers=6) as executor:
                    futures = [executor.submit(process_symbol, sym, selected_date) for sym in symbols]
                    results = [f.result() for f in futures if f.result() is not None]

            if results:
                df_symbols = pd.DataFrame(results)

                # Format the numbers to display as "1.000.000" instead of "1000000"
                df_display = df_symbols.copy()
                for col in ['cumulative_value_buy', 'cumulative_value_sell', 'cumulative_value_net']:
                    df_display[col] = df_display[col].map(lambda x: f"{x:,.0f}".replace(",", "."))

                # Display the formatted table
                st.subheader("📋 Bảng Dòng Tiền Mua/Bán/Ròng Lũy Kế (VND)")
                st.dataframe(df_display, use_container_width=True)

                # Split the screen into two columns
                col1, col2 = st.columns(2)

                with col1:
                    # Top 10 stocks with the highest net cash flow
                    top_10_net_positive = df_symbols.nlargest(10, 'cumulative_value_net')
                    st.subheader("🔝 Top 10 Cổ Phiếu Có Dòng Tiền Ròng Lớn Nhất")
                    top_10_net_positive_display = top_10_net_positive[['symbol', 'cumulative_value_net']]
                    top_10_net_positive_display['cumulative_value_net'] = top_10_net_positive_display['cumulative_value_net'].map(lambda x: f"{x:,.0f}".replace(",", "."))
                    st.dataframe(top_10_net_positive_display, use_container_width=True)

                with col2:
                    # Top 10 stocks with the lowest net cash flow
                    top_10_net_negative = df_symbols.nsmallest(10, 'cumulative_value_net')
                    st.subheader("🔻 Top 10 Cổ Phiếu Có Dòng Tiền Ròng Thấp Nhất")
                    top_10_net_negative_display = top_10_net_negative[['symbol', 'cumulative_value_net']]
                    top_10_net_negative_display['cumulative_value_net'] = top_10_net_negative_display['cumulative_value_net'].map(lambda x: f"{x:,.0f}".replace(",", "."))
                    st.dataframe(top_10_net_negative_display, use_container_width=True)

            else:
                st.warning("Không thể phân tích dòng tiền các mã cổ phiếu này.")
        else:
            st.warning("Không có mã cổ phiếu nào để phân tích.")

                
# ==== TAB 4 ====

with tab4:
    st.title("📊 Phân Tích Chỉ Số Tài Chính Cơ Bản")

    st.markdown("""
    Nhập mã cổ phiếu để xem các chỉ số tài chính như ROE, ROA, EPS, Nợ/Vốn chủ sở hữu, v.v.  
    Nguồn dữ liệu: VCI (vnstock)
    """)

    symbol = st.text_input("Nhập mã cổ phiếu:", value="VNM", key="symbol_tab4").strip().upper()
    period = st.selectbox("Chọn chu kỳ:", ["year", "quarter"], index=0)
    lang = st.radio("Ngôn ngữ hiển thị:", ["vi", "en"], horizontal=True)

    if st.button("🔍 Lấy dữ liệu", key="analyze_tab4"):
        try:
            from vnstock import Vnstock
            stock = Vnstock().stock(symbol=symbol, source='VCI')
            
            
            # 1. Hiển thị bảng chỉ số tài chính
            st.subheader("📈 Chỉ số tài chính")
            df_ratio = stock.finance.ratio(period=period, lang=lang, dropna=True)
            if df_ratio is not None and not df_ratio.empty:
                st.success("Dữ liệu chỉ số tài chính đã được lấy thành công!")
                st.dataframe(df_ratio, use_container_width=True)
            else:
                st.warning("Không có dữ liệu chỉ số tài chính cho mã này.")
                    
                # 2. Bảng cân đối kế toán
            st.subheader("💰 Bảng cân đối kế toán")
            df_balance = stock.finance.balance_sheet(period=period, lang=lang, dropna=True)
            if df_balance is not None and not df_balance.empty:
                st.dataframe(df_balance, use_container_width=True)
            else:
                st.warning("Không có dữ liệu bảng cân đối kế toán.")
            
            # 3. Báo cáo kết quả kinh doanh
            st.subheader("📊 Báo cáo kết quả kinh doanh")
            df_income = stock.finance.income_statement(period=period, lang=lang, dropna=True)
            if df_income is not None and not df_income.empty:
                st.dataframe(df_income, use_container_width=True)
            else:
                st.warning("Không có dữ liệu báo cáo kết quả kinh doanh.")
            
            # 4. Báo cáo lưu chuyển tiền tệ
            st.subheader("💵 Báo cáo lưu chuyển tiền tệ")
            df_cashflow = stock.finance.cash_flow(period=period, lang=lang, dropna=True)
            if df_cashflow is not None and not df_cashflow.empty:
                st.dataframe(df_cashflow, use_container_width=True)
            else:
                st.warning("Không có dữ liệu báo cáo lưu chuyển tiền tệ.")
            
        except Exception as e:
            st.error(f"Đã xảy ra lỗi khi lấy dữ liệu: {e}")
            
            
          
# ==== TAB 5 ====            
with tab5:
    st.title("📉 Biểu Đồ Nến Nhật – Giá Cổ Phiếu")

    st.markdown("Chọn mã cổ phiếu, khoảng thời gian và khung thời gian để xem biểu đồ giá.")

    symbol = st.text_input("Nhập mã cổ phiếu:", value="VNM", key="symbol_tab5").strip().upper()
    start_date = st.date_input("Ngày bắt đầu", value=date(2025, 1, 1))
    end_date = st.date_input("Ngày kết thúc", value=date.today())

    timeframe = st.selectbox("Khung thời gian:", options=["D", "W", "M"], index=0, 
                             format_func=lambda x: {"D": "Ngày", "W": "Tuần", "M": "Tháng"}[x])

    # Tùy chọn hiển thị các đường MA
    show_ma5 = st.checkbox("Hiển thị MA 5", value=True)
    show_ma20 = st.checkbox("Hiển thị MA 20", value=True)
    show_ma50 = st.checkbox("Hiển thị MA 50", value=True)

    if st.button("📊 Hiển thị biểu đồ", key="btn_tab5"):
        try:
            from vnstock import Vnstock
            import plotly.graph_objects as go

            stock = Vnstock().stock(symbol=symbol, source='VCI')
            df_candle = stock.quote.history(start=str(start_date), end=str(end_date))

            if df_candle is None or df_candle.empty or 'time' not in df_candle.columns:
                st.warning("Không có dữ liệu cho mã cổ phiếu và khoảng thời gian đã chọn.")
            else:
                df_candle['time'] = pd.to_datetime(df_candle['time'])
                df_candle.set_index('time', inplace=True)

                if timeframe in ['W', 'M']:
                    df_candle = df_candle.resample(timeframe).agg({
                        'open': 'first',
                        'high': 'max',
                        'low': 'min',
                        'close': 'last',
                        'volume': 'sum'
                    }).dropna()

                df_candle.reset_index(inplace=True)
                
                # Chuyển đổi thời gian sang định dạng ngày ngắn gọn
                df_candle['time'] = pd.to_datetime(df_candle['time']).dt.strftime('%d-%m')

                # Tính các đường MA
                df_candle['MA5'] = df_candle['close'].rolling(window=5).mean()
                df_candle['MA20'] = df_candle['close'].rolling(window=20).mean()
                df_candle['MA50'] = df_candle['close'].rolling(window=50).mean()

                fig = go.Figure(data=[go.Candlestick(
                    x=df_candle['time'],
                    open=df_candle['open'],
                    high=df_candle['high'],
                    low=df_candle['low'],
                    close=df_candle['close'],
                    increasing_line_color='green',
                    decreasing_line_color='red',
                    name='Nến Nhật'
                )])

                # Thêm các đường MA nếu người dùng chọn hiển thị
                if show_ma5:
                    fig.add_trace(go.Scatter(
                        x=df_candle['time'],
                        y=df_candle['MA5'],
                        mode='lines',
                        name='MA 5',
                        line=dict(color='blue', width=2)
                    ))

                if show_ma20:
                    fig.add_trace(go.Scatter(
                        x=df_candle['time'],
                        y=df_candle['MA20'],
                        mode='lines',
                        name='MA 20',
                        line=dict(color='orange', width=2)
                    ))

                if show_ma50:
                    fig.add_trace(go.Scatter(
                        x=df_candle['time'],
                        y=df_candle['MA50'],
                        mode='lines',
                        name='MA 50',
                        line=dict(color='purple', width=2)
                    ))

                fig.update_layout(
                    title=f'Biểu đồ Nến Nhật: {symbol} ({ {"D":"Ngày","W":"Tuần","M":"Tháng"}[timeframe] })',
                    xaxis_title='Ngày',
                    yaxis_title='Giá',
                    xaxis_rangeslider_visible=False,
                    height=500,
                    margin=dict(l=0, r=0, t=40, b=0),  # Loại bỏ các khoảng trống
                    xaxis=dict(
                        showgrid=False,
                        zeroline=False,
                        type='category',  # Loại bỏ các ngày không có giao dịch
                        tickmode='array',
                        tickvals=df_candle['time'],  # Hiển thị các giá trị có dữ liệu
                        tickangle=45  # Góc quay các nhãn để tránh chồng chéo
                    ),
                    yaxis=dict(
                        showgrid=False,
                        zeroline=False
                    )
                )

                st.plotly_chart(fig, use_container_width=True)
                
                # Biểu đồ khối lượng
                fig_volume = go.Figure()
                fig_volume.add_trace(go.Bar(
                    x=df_candle['time'],
                    y=df_candle['volume'],
                    marker_color='orange',
                    name='Khối lượng'
                ))

                fig_volume.update_layout(
                    title='📊 Khối Lượng Giao Dịch',
                    xaxis_title='Ngày',
                    yaxis_title='Khối lượng',
                    height=300,
                    margin=dict(l=0, r=0, t=40, b=0),  # Loại bỏ các khoảng trống
                    xaxis=dict(
                        showgrid=False,
                        zeroline=False,
                        type='category',  # Loại bỏ các ngày không có giao dịch
                        tickmode='array',
                        tickvals=df_candle['time'],  # Hiển thị các giá trị có dữ liệu
                        tickangle=45  # Góc quay các nhãn để tránh chồng chéo
                    ),
                    yaxis=dict(
                        showgrid=False,
                        zeroline=False
                    )
                )

                # Hiển thị biểu đồ khối lượng
                st.plotly_chart(fig_volume, use_container_width=True)

                st.download_button(
                    label="📥 Tải dữ liệu giá lịch sử (.CSV)",
                    data=df_candle.to_csv(index=False).encode("utf-8"),
                    file_name=f"{symbol}_gia_lich_su_{timeframe}.csv",
                    mime="text/csv"
                )

        except Exception as e:
            st.error(f"Đã xảy ra lỗi: {e}")

# ==== TAB 6 ====  
with tab6:
    st.title("📈 Cập nhật Giá Cổ Phiếu Realtime")
    
    st.markdown("Nhập mã cổ phiếu để xem dữ liệu giao dịch realtime theo 5 phút.")
    
    symbol = st.text_input("Nhập mã cổ phiếu:", value="VNM", key="symbol_tab6").strip().upper()
    
    # Tùy chọn số lượng dữ liệu trả về
    page_size = st.number_input("Chọn số lượng bản ghi:", min_value=1, max_value=50000, value=10000)
    
    # Lấy và hiển thị thông tin realtime khi nhấn nút
    if st.button("📊 Hiển thị giá cổ phiếu realtime", key="btn_tab6"):
        try:
            # Khởi tạo đối tượng stock
            stock = Vnstock().stock(symbol=symbol, source='VCI')

            # Lấy dữ liệu giao dịch intraday (thời gian thực)
            df_realtime = stock.quote.intraday(symbol=symbol, page_size=page_size)

            if df_realtime is None or df_realtime.empty:
                st.warning(f"Không có dữ liệu giao dịch realtime cho mã cổ phiếu {symbol}.")
            else:
                # Chuyển đổi dữ liệu thời gian về đúng định dạng
                df_realtime['time'] = pd.to_datetime(df_realtime['time'])
                
                # Thiết lập thời gian 5 phút
                df_realtime.set_index('time', inplace=True)
                df_realtime['5_min_interval'] = df_realtime.index.floor('5T')  # Chuyển các thời gian về khung 5 phút
                
                # Tính toán volume buy và volume sell dựa trên match_type
                df_realtime['volume_buy'] = df_realtime.apply(lambda row: row['volume'] if row['match_type'] == 'Buy' else 0, axis=1)
                df_realtime['volume_sell'] = df_realtime.apply(lambda row: row['volume'] if row['match_type'] == 'Sell' else 0, axis=1)
                
                # Nhóm theo khung thời gian 5 phút và tính toán các giá trị cần thiết
                df_grouped = df_realtime.groupby('5_min_interval').agg(
                    volume_buy=('volume_buy', 'sum'),  # Tổng volume của các giao dịch mua
                    volume_sell=('volume_sell', 'sum'),  # Tổng volume của các giao dịch bán
                    avg_price=('price', 'mean')  # Tính giá trung bình (mean)
                ).reset_index()

                # Tính toán net (volume_buy - volume_sell)
                df_grouped['net'] = df_grouped['volume_buy'] - df_grouped['volume_sell']
                
                
                # Tính tổng các giá trị
                total_volume_buy = df_grouped['volume_buy'].sum()
                total_volume_sell = df_grouped['volume_sell'].sum()
                total_net = df_grouped['net'].sum()
                avg_price_total = df_grouped['avg_price'].mean()
                
                # Hiển thị tổng các giá trị
                st.markdown(f"### Tổng Dữ Liệu Giao Dịch (Cổ Phiếu: {symbol})")
                st.markdown(f"- **Tổng volume mua:** {total_volume_buy:,.0f}")
                st.markdown(f"- **Tổng volume bán:** {total_volume_sell:,.0f}")
                st.markdown(f"- **Tổng net (Mua - Bán):** {total_net:,.0f}")
                st.markdown(f"- **Giá trung bình:** {avg_price_total:,.2f}")

                # Sắp xếp cột theo thứ tự yêu cầu
                df_grouped = df_grouped[['5_min_interval', 'avg_price', 'volume_buy', 'volume_sell', 'net']]
                df_grouped.rename(columns={'5_min_interval': 'time'}, inplace=True)

                # Hiển thị bảng dữ liệu theo yêu cầu
                st.write(f"Thông tin giá cổ phiếu {symbol} realtime theo từng khoảng 5 phút:")
                st.dataframe(df_grouped.style.format({'avg_price': '{:,.2f}', 'volume_buy': '{:,.0f}', 'volume_sell': '{:,.0f}', 'net': '{:,.0f}'}), use_container_width=True)
                
                # Tùy chọn tải về dữ liệu
                st.download_button(
                    label="📥 Tải dữ liệu realtime (.CSV)",
                    data=df_grouped.to_csv(index=False).encode("utf-8"),
                    file_name=f"{symbol}_gia_realtime_5phut.csv",
                    mime="text/csv"
                )

        except Exception as e:
            st.error(f"Đã xảy ra lỗi khi lấy dữ liệu realtime: {e}")

            
# ==== TAB 7 ====
with tab7:
    st.title("📊 Phân Tích Cổ Phiếu (Dữ liệu Intraday)")

    st.markdown("Nhập mã cổ phiếu và số bản ghi để phân tích dữ liệu cổ phiếu theo từng phút.")

    symbol = st.text_input("Nhập mã cổ phiếu:", value="VNM", key="symbol_tab7").strip().upper()
    page_size = st.number_input("Chọn số lượng bản ghi (giao dịch):", min_value=1, max_value=50000, value=10000)

    if st.button("📈 Phân tích cổ phiếu", key="btn_tab7"):
        try:
            # Khởi tạo đối tượng lấy dữ liệu
            stock = Vnstock().stock(symbol=symbol, source='VCI')
            df_intraday = stock.quote.intraday(symbol=symbol, page_size=page_size)

            if df_intraday is None or df_intraday.empty:
                st.warning(f"Không có dữ liệu intraday cho mã {symbol}.")
            else:
                df_intraday['time'] = pd.to_datetime(df_intraday['time'])
                df_intraday.set_index('time', inplace=True)

                # Gộp theo từng phút
                df_intraday['minute'] = df_intraday.index.floor('T')  # 'T' là viết tắt cho 'minutely'

                # Tính volume mua & bán
                df_intraday['volume_buy'] = df_intraday.apply(lambda x: x['volume'] if x['match_type'] == 'Buy' else 0, axis=1)
                df_intraday['volume_sell'] = df_intraday.apply(lambda x: x['volume'] if x['match_type'] == 'Sell' else 0, axis=1)

                # Nhóm theo từng phút
                df_min = df_intraday.groupby('minute').agg(
                    volume_buy=('volume_buy', 'sum'),
                    volume_sell=('volume_sell', 'sum'),
                    avg_price=('price', 'mean')
                ).reset_index()

                # Tính dòng tiền (Value = Giá * Volume)
                df_min['value_buy'] = df_min['volume_buy'] * df_min['avg_price'] * 1000
                df_min['value_sell'] = df_min['volume_sell'] * df_min['avg_price'] * 1000
                df_min['net'] = df_min['volume_buy'] - df_min['volume_sell']
                df_min['net_value'] = df_min['value_buy'] - df_min['value_sell'] 
                
                # Tính khối lượng mua/bán lũy kế
                df_min['cumulative_volume_buy'] = df_min['volume_buy'].cumsum()
                df_min['cumulative_volume_sell'] = df_min['volume_sell'].cumsum()
                df_min['cumulative_volume_net'] = df_min['cumulative_volume_buy'] - df_min['cumulative_volume_sell']

                # Tính dòng tiền lũy kế
                df_min['cumulative_volume_net'] = df_min['net'].cumsum()
                df_min['cumulative_net'] = df_min['net_value'].cumsum()
                
                
                # Hiển thị bảng
                st.markdown(f"### Dữ liệu cổ phiếu theo phút cho mã: **{symbol}**")
                st.dataframe(df_min.style.format({'avg_price': '{:,.2f}', 'volume_buy': '{:,.0f}', 'volume_sell': '{:,.0f}', 'net': '{:,.0f}', 'value_buy': '{:,.2f}',
                'value_sell': '{:,.2f}', 'net_value': '{:,.2f}', 'cumulative_volume_buy': '{:,.2f}','cumulative_volume_sell': '{:,.2f}','cumulative_volume_net': '{:,.2f}', 'cumulative_net': '{:,.2f}'}), use_container_width=True)

                #1 Biểu đồ dòng tiền theo Volume
                st.markdown("### 📊 Biểu đồ dòng tiền theo phút")

                fig = go.Figure()

                # Volume mua - màu xanh (dương)
                fig.add_trace(go.Bar(
                    x=df_min['minute'],
                    y=df_min['volume_buy'],
                    name='Volume Mua',
                    marker=dict(color='#2ECC71', line=dict(width=0))
                ))

                # Volume bán - màu đỏ (âm)
                fig.add_trace(go.Bar(
                    x=df_min['minute'],
                    y=-df_min['volume_sell'],  # âm để hiển thị bên dưới trục
                    name='Volume Bán',
                    marker=dict(color='#E74C3C', line=dict(width=0))
                ))

                # Net Volume - chỉ là line không có markers
                fig.add_trace(go.Scatter(
                    x=df_min['minute'],
                    y=df_min['volume_buy'] - df_min['volume_sell'],  # Net Volume
                    mode='lines',
                    name='Net Volume',
                    line=dict(color='#9B59B6', width=2),
                    yaxis='y2'
                ))

                # Cập nhật layout
                fig.update_layout(
                    barmode='relative',
                    title=f"📊 Dòng tiền theo phút - {symbol}",
                    xaxis_title="Thời gian",
                    yaxis=dict(
                        title="Volume (Cổ phiếu)",
                        side="left"
                    ),
                    yaxis2=dict(
                        title="Net Volume",
                        overlaying='y',
                        side='right',
                        showgrid=False
                    ),
                    template='plotly_dark',
                    hovermode='x unified',
                    legend=dict(orientation='h', yanchor='bottom', y=1.02, xanchor='right', x=1)
                )

                st.plotly_chart(fig, use_container_width=True)
                
                
                #2 Biểu đồ dòng tiền theo giá trị
                fig2 = go.Figure()

                # Giá trị mua - cột màu xanh
                fig2.add_trace(go.Bar(
                    x=df_min['minute'],
                    y=df_min['value_buy'],
                    name='Giá trị Mua (VND)',
                    marker=dict(color='#2ECC71', line=dict(width=0)),
                    yaxis='y'
                ))

                # Giá trị bán - cột màu đỏ
                fig2.add_trace(go.Bar(
                    x=df_min['minute'],
                    y=-df_min['value_sell'],  # Hiển thị giá trị bán dưới trục
                    name='Giá trị Bán (VND)',
                    marker=dict(color='#E74C3C', line=dict(width=0)),
                    yaxis='y'
                ))

                # Net Value - đường màu tím
                fig2.add_trace(go.Scatter(
                    x=df_min['minute'],
                    y=df_min['value_buy'] - df_min['value_sell'],
                    mode='lines',
                    name='Net Value (VND)',
                    line=dict(color='#9B59B6', width=2),
                    yaxis='y'
                ))

                # Cập nhật layout
                fig2.update_layout(
                    title="💰 Dòng tiền theo giá trị (VND) theo phút",
                    xaxis_title="Thời gian",
                    yaxis_title="Giá trị (VND)",
                    template='plotly_dark',
                    barmode='relative',  # Cho phép cột âm và dương chồng lên nhau
                    hovermode='x unified',
                    legend=dict(orientation='h', yanchor='bottom', y=1.02, xanchor='right', x=1)
                )

                st.plotly_chart(fig2, use_container_width=True)
                
                              

                # Biểu đồ Khối lượng lũy kế
                fig5 = go.Figure()

                # Khối lượng mua lũy kế - cột dương
                fig5.add_trace(go.Bar(
                    x=df_min['minute'],
                    y=df_min['cumulative_volume_buy'],
                    name='Khối lượng Mua lũy kế',
                    marker=dict(color='#2ECC71', line=dict(width=0)),
                    yaxis='y'
                ))

                # Khối lượng bán lũy kế - cột âm
                fig5.add_trace(go.Bar(
                    x=df_min['minute'],
                    y=-df_min['cumulative_volume_sell'],
                    name='Khối lượng Bán lũy kế',
                    marker=dict(color='#E74C3C', line=dict(width=0)),
                    yaxis='y'
                ))

                # Khối lượng ròng lũy kế - line màu xanh dương đậm
                fig5.add_trace(go.Scatter(
                    x=df_min['minute'],
                    y=df_min['cumulative_volume_net'],
                    mode='lines',
                    name='Khối lượng ròng lũy kế',
                    line=dict(color='#9B59B6', width=2),
                    yaxis='y'
                ))

                fig5.update_layout(
                    title="📈 Khối lượng ròng lũy kế theo phút",
                    xaxis_title="Thời gian",
                    yaxis_title="Khối lượng (Cổ phiếu)",
                    template='plotly_dark',
                    barmode='relative',
                    hovermode='x unified',
                    legend=dict(orientation='h', yanchor='bottom', y=1.02, xanchor='right', x=1)
                )

                st.plotly_chart(fig5, use_container_width=True)
                
                #4 Biểu đồ dòng tiền lũy kế
                fig6 = px.line(
                    df_min, x='minute', y='cumulative_net',
                    title="📈 Giá trị Dòng tiền ròng lũy kế theo phút",
                    labels={'cumulative_net': 'Dòng tiền ròng lũy kế (VND)', 'minute': 'Thời gian'}
                )
                fig6.update_traces(line=dict(color='#2980B9', width=2))
                st.plotly_chart(fig6, use_container_width=True)

                                
                

        except Exception as e:
            st.error(f"Đã xảy ra lỗi: {str(e)}")


           
