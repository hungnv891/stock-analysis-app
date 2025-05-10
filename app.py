import streamlit as st
from analyzer import analyze_stock, export_to_excel
import os
import pandas as pd
from datetime import date
from vnstock import Vnstock
import plotly.graph_objects as go

st.set_page_config(page_title='Phân Tích Cổ Phiếu', layout='wide')
tab1, tab2, tab3, tab4, tab5, tab6 = st.tabs([
    '📈 Dòng Tiền Theo Từng Mã',
    '🏭 Dòng Tiền Theo Nhóm Ngành',
    '📝 Nhập Mã Tùy Chọn',
    '📊 Phân Tích Cơ Bản',
    '📉 Biểu Đồ Giá',
    '📈 Cập nhật Giá Cổ Phiếu Realtime'
])


# ==== TAB 1 ====
with tab1:
    st.title("📊 Phân Tích Dòng Tiền Cổ Phiếu")

    st.markdown("""
    Nhập mã cổ phiếu (ví dụ: **VNM**, **SSI**, **FPT**) và chọn ngày để phân tích giao dịch từ nguồn TCBS.
    """)

    symbol = st.text_input("Nhập mã cổ phiếu:", value="VNM").strip().upper()
    selected_date = st.date_input("Chọn ngày giao dịch:", value=date.today())

    if st.button("Phân Tích"):
        if symbol:
            with st.spinner("Đang tải và phân tích dữ liệu..."):
                result = analyze_stock(symbol, selected_date)

            if result is not None:
                summary = result['summary']
                resampled = result['resampled']
                df = result['df']
                chart_paths = result['chart_paths']

                st.success("Phân tích hoàn tất!")
                
                # Hiển thị phần tóm tắt
                st.subheader("📊 Tóm Tắt Phân Tích")
                
                col1, col2 = st.columns(2)
                with col1:
                    st.metric("Tổng dòng tiền vào (VND)", summary['Tổng dòng tiền vào (VND)'])
                    st.metric("Tổng dòng tiền ra (VND)", summary['Tổng dòng tiền ra (VND)'])
                    st.metric("Dòng tiền ròng (VND)", summary['Dòng tiền ròng (VND)'])
                    st.metric("Tổng số lệnh mua", summary['Tổng số lệnh mua'])
                    st.metric("Tổng số lệnh bán", summary['Tổng số lệnh bán'])

                with col2:
                    st.metric("Khối lượng TB lệnh mua", f"{summary['Khối lượng trung bình lệnh mua']:,.2f}")
                    st.metric("Khối lượng TB lệnh bán", f"{summary['Khối lượng trung bình lệnh bán']:,.2f}")
                    st.metric("Tỷ lệ mua/bán", f"{summary['Tỷ lệ khối lượng trung bình mua/bán']:,.2f}")
                    st.metric("Giá cao nhất", f"{summary['Giá cao nhất']:,.2f}")
                    st.metric("Giá thấp nhất", f"{summary['Giá thấp nhất']:,.2f}")

                if chart_paths:
                    st.subheader("📈 Biểu đồ phân tích:")
                    for path in chart_paths:
                        if os.path.exists(path):
                            st.image(path, use_container_width=True)
                            os.remove(path)  # XÓA FILE sau khi đã hiển thị
                        else:
                            st.warning(f"Không tìm thấy biểu đồ: {path}")
                            

                excel_path = export_to_excel(resampled, df, symbol, selected_date)
                if excel_path and os.path.exists(excel_path):
                    st.subheader("📥 Tải xuống dữ liệu:")
                    with open(excel_path, "rb") as f:
                        st.download_button(
                            label="📊 Tải Excel kết quả",
                            data=f,
                            file_name=os.path.basename(excel_path),
                            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                        )
                else:
                    st.warning("Không thể tạo file Excel.")
            else:
                st.error("Không thể phân tích mã cổ phiếu này. Hãy thử lại với mã khác.")
        else:
            st.warning("Vui lòng nhập mã cổ phiếu.")

# ==== TAB 2 ====
from concurrent.futures import ThreadPoolExecutor

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
            result = analyze_stock(symbol, selected_date)
            if result:
                def parse_currency(value):
                    if isinstance(value, str):
                        return float(value.replace(".", "").replace(",", "").replace("−", "-"))
                    return float(value)
                    
                def format_number(value):
                    return "{:,.0f}".format(value).replace(",", ".")    

                in_flow = parse_currency(result['summary']['Tổng dòng tiền vào (VND)'])
                out_flow = parse_currency(result['summary']['Tổng dòng tiền ra (VND)'])
                net_flow = parse_currency(result['summary']['Dòng tiền ròng (VND)'])
                return {"symbol": symbol, "in": in_flow, "out": out_flow, "net": net_flow}
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
            for col in ['in', 'out', 'net']:
                df_display[col] = df_display[col].map(lambda x: f"{x:,.0f}".replace(",", "."))

            # Hiển thị bảng định dạng
            st.subheader("📋 Bảng Dòng Tiền (VND)")
            st.dataframe(df_display, use_container_width=True)

            import altair as alt

            st.subheader(f'📊 Biểu Đồ Dòng Tiền Nhóm: {selected_sector}')

            # Dữ liệu dạng long cho biểu đồ cột
            df_melted = df_sector.melt(id_vars="symbol", value_vars=["in", "out"], var_name="type", value_name="value")

            bars = alt.Chart(df_melted).mark_bar().encode(
                x=alt.X('symbol:N', title='Mã cổ phiếu'),
                xOffset='type:N',
                y=alt.Y('value:Q', title='VND'),
                color=alt.Color('type:N', scale=alt.Scale(domain=['in', 'out'], range=['#2E86AB', '#E74C3C'])),
                tooltip=['symbol', 'type', alt.Tooltip('value:Q', format=',')]
            ).properties(
                width=700,
                height=400
            )

            line = alt.Chart(df_sector).mark_line(color='purple', strokeWidth=3).encode(
                x=alt.X('symbol:N', title='Mã cổ phiếu'),
                y=alt.Y('net:Q', title='VND'),
                tooltip=['symbol', alt.Tooltip('net:Q', format=',')]
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
    st.title('📝 Phân Tích Dòng Tiền Theo Danh Sách Tùy Chọn')

    st.markdown("Nhập tối đa **10 mã cổ phiếu**, cách nhau bởi dấu phẩy (`,`)")

    custom_input = st.text_input("Nhập mã cổ phiếu:", placeholder="VD: VNM, SSI, FPT, HPG")
    selected_date_custom = st.date_input('Chọn ngày giao dịch:', value=date.today(), key='date_custom')
    analyze_custom_button = st.button('🔍 Phân Tích Danh Sách')

    if analyze_custom_button:
        symbols = [s.strip().upper() for s in custom_input.split(",") if s.strip()]
        symbols = list(dict.fromkeys(symbols))
        if len(symbols) == 0:
            st.warning("Vui lòng nhập ít nhất 1 mã cổ phiếu.")
        elif len(symbols) > 10:
            st.error("Chỉ phân tích tối đa 10 mã cổ phiếu.")
        else:
            st.info(f"Đang phân tích {len(symbols)} mã...")

            with st.spinner("Đang xử lý..."):
                with ThreadPoolExecutor(max_workers=6) as executor:
                    futures = [executor.submit(process_symbol, sym, selected_date_custom) for sym in symbols]
                    results = [f.result() for f in futures if f.result() is not None]

            if results:
                df_custom = pd.DataFrame(results)
                df_display = df_custom.copy()
                for col in ['in', 'out', 'net']:
                    df_display[col] = df_display[col].map(lambda x: f"{x:,.0f}".replace(",", "."))

                st.subheader("📋 Bảng Dòng Tiền (VND)")
                st.dataframe(df_display, use_container_width=True)

                import altair as alt

                st.subheader('📊 Biểu Đồ Dòng Tiền')

                df_melted = df_custom.melt(id_vars="symbol", value_vars=["in", "out"], var_name="type", value_name="value")

                bars = alt.Chart(df_melted).mark_bar().encode(
                    x=alt.X('symbol:N', title='Mã cổ phiếu'),
                    xOffset='type:N',
                    y=alt.Y('value:Q', title='VND'),
                    color=alt.Color('type:N', scale=alt.Scale(domain=['in', 'out'], range=['#2E86AB', '#E74C3C'])),
                    tooltip=['symbol', 'type', alt.Tooltip('value:Q', format=',')]
                ).properties(width=700, height=400)

                line = alt.Chart(df_custom).mark_line(color='purple', strokeWidth=3).encode(
                    x=alt.X('symbol:N'),
                    y=alt.Y('net:Q'),
                    tooltip=['symbol', alt.Tooltip('net:Q', format=',')]
                )

                chart = (bars + line).resolve_scale(y='shared').properties(width=700, height=400)
                st.altair_chart(chart, use_container_width=True)
            else:
                st.warning("Không thể phân tích các mã đã nhập.")
                
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


            
