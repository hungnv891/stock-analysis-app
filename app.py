import streamlit as st
from analyzer import analyze_stock, export_to_excel
import os
import pandas as pd
from datetime import date

st.set_page_config(page_title='Phân Tích Cổ Phiếu', layout='wide')
tab1, tab2 = st.tabs(['📈 Phân Tích Từng Mã', '🏭 Dòng Tiền Theo Nhóm Ngành'])

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
        'Ngân hàng': ['VCB', 'CTG', 'BID', 'TCB', 'MBB', 'ACB', 'HDB'],
        'Chứng khoán': ['SSI', 'VND', 'HCM', 'VCI', 'FTS', 'CTS'],
        'Thép': ['HPG', 'HSG', 'NKG', 'TLH'],
        'Bất động sản': ['VIC', 'VHM', 'NLG', 'KDH', 'DXG', 'HDG'],
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
        'Vận tải': ['PVT', 'HAH', 'GMD', 'VNS'],
        'Nhựa': ['AAA', 'BMP', 'NTP', 'DNP'],
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
            st.dataframe(df_sector, use_container_width=True)

            import altair as alt

            st.subheader(f'📊 Biểu Đồ Dòng Tiền Nhóm: {selected_sector}')

            # Tạo DataFrame dạng long format cho biểu đồ
            df_melted = df_sector.melt(id_vars="symbol", value_vars=["in", "out"], var_name="type", value_name="value")
            
            # Tạo biểu đồ cột cho dòng tiền vào và ra
            bars = alt.Chart(df_melted).mark_bar().encode(
                x=alt.X('symbol:N', title='Mã cổ phiếu'),
                y=alt.Y('value:Q', title='VND'),
                color=alt.Color('type:N', scale=alt.Scale(domain=['in', 'out'], range=['green', 'red'])),
                tooltip=['symbol', 'type', 'value']
            ).properties(
                width=700,
                height=400
            )
            
            # Tạo biểu đồ đường cho dòng tiền ròng
            line = alt.Chart(df_sector).mark_line(color='purple', strokeWidth=3).encode(
                x=alt.X('symbol:N', title='Mã cổ phiếu'),
                y=alt.Y('net:Q', title='VND'),
                tooltip=['symbol', 'net']
            )
            
            # Kết hợp biểu đồ
            chart = (bars + line).properties(
                width=700,
                height=400
            ).resolve_scale(
                y='shared'
            )
            
            st.altair_chart(chart, use_container_width=True)
        else:
            st.warning("Không thể phân tích dòng tiền nhóm ngành này.")
