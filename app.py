from analyzer import analyze_stock, export_to_excel
from datetime import date
from vnstock import Vnstock
from concurrent.futures import ThreadPoolExecutor
from plotly.subplots import make_subplots
from io import StringIO
from datetime import timedelta
import plotly.graph_objects as go
import plotly.express as px
import matplotlib.pyplot as plt
import seaborn as sns
import math
import streamlit.components.v1 as components
import time
import os
import pandas as pd
import streamlit as st
import seaborn as sns
import re
import plotly.figure_factory as ff



st.set_page_config(page_title='Phân Tích Cổ Phiếu', layout='wide')
tab1, tab2, tab3, tab4, tab6, tab8 = st.tabs([
    '💰 Phân Tích Dòng Tiền Cổ Phiếu',
    '🗃️ Phân Tích Dòng Tiền Theo Nhóm',    
    '📊 Biểu Đồ Giá',
    '📈 Cập nhật Giá Cổ Phiếu Realtime',
    '💹 Phân Tích Thị Trường',
    '💼 Phân Tích Tài Chính Doanh Nghiệp'
    
])
# Hàm chuyển đổi số thành dạng rút gọn K, M, B
def format_number(value):
    if abs(value) >= 1_000_000_000:
        return f"{value / 1_000_000_000:.1f}B"  # Tỷ (Billion)
    elif abs(value) >= 1_000_000:
        return f"{value / 1_000_000:.1f}M"  # Triệu (Million)
    elif abs(value) >= 1_000:
        return f"{value / 1_000:.1f}K"  # Nghìn (Thousand)
    else:
        return f"{value:.0f}"  # Không thay đổi nếu nhỏ hơn 1000
        
# ==== TAB 1 ====
with tab1:
    st.title("💰 Phân Tích Cổ Phiếu (Dữ liệu Intraday)")

    st.markdown("Nhập mã cổ phiếu và số bản ghi để phân tích dữ liệu cổ phiếu theo từng phút.")

    symbol = st.text_input("Nhập mã cổ phiếu:", value="VNM", key="symbol_tab7").strip().upper()
    page_size = st.number_input("Chọn số lượng bản ghi (giao dịch):", min_value=1, max_value=50000, value=10000)

    if st.button("💰 Phân tích cổ phiếu", key="btn_tab7"):
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

                # 1. Tính toán Volume mua, bán và volume ròng theo mức giá (Net Volume theo Price Level)
                df_price_level = df_intraday.groupby('price').agg(
                    volume_buy=('volume_buy', 'sum'),
                    volume_sell=('volume_sell', 'sum'),
                ).reset_index()

                # Tính volume ròng theo giá
                df_price_level['net_volume'] = df_price_level['volume_buy'] - df_price_level['volume_sell']

                # Tính giá trị ròng = volume * giá
                df_price_level['net_value'] = df_price_level['net_volume'] * df_price_level['price'] *1000

                # Tính giá trị mua và bán
                df_price_level['buy_value'] = df_price_level['volume_buy'] * df_price_level['price'] *1000
                df_price_level['sell_value'] = df_price_level['volume_sell'] * df_price_level['price'] *1000

                # 2. Vẽ biểu đồ Volume mua, bán, và volume ròng theo mức giá (Đồ thị 1)
                fig8 = go.Figure()

                # Volume mua theo mức giá - màu xanh dương
                fig8.add_trace(go.Bar(
                    x=df_price_level['price'],
                    y=df_price_level['volume_buy'],
                    name='Volume Mua',
                    marker=dict(color='#2ECC71', line=dict(width=0)),
                ))

                # Volume bán theo mức giá - màu đỏ
                fig8.add_trace(go.Bar(
                    x=df_price_level['price'],
                    y=-df_price_level['volume_sell'],  # Dùng dấu âm để hiển thị dưới trục
                    name='Volume Bán',
                    marker=dict(color='#E74C3C', line=dict(width=0)),
                ))

                # Volume ròng theo mức giá - đường màu tím
                fig8.add_trace(go.Scatter(
                    x=df_price_level['price'],
                    y=df_price_level['net_volume'],
                    mode='lines+markers',
                    name='Net Volume',
                    line=dict(color='#9B59B6', width=2),
                    marker=dict(color='#9B59B6', size=6, symbol='circle')  # Dot với đường tròn
                ))

                # Cập nhật layout cho biểu đồ Volume
                fig8.update_layout(
                    title="📊 Volume Mua, Bán và Volume Ròng theo Mức Giá",
                    xaxis_title="Mức Giá (VND)",
                    yaxis_title="Volume (Cổ phiếu)",
                    template='plotly_dark',
                    hovermode='x unified',
                    barmode='relative',
                    legend=dict(orientation='h', yanchor='bottom', y=1.02, xanchor='right', x=1)
                )

                # Hiển thị biểu đồ Volume
                st.plotly_chart(fig8, use_container_width=True)

                # 3. Vẽ biểu đồ Giá trị mua, bán, và giá trị ròng theo mức giá (Đồ thị 2)
                fig9 = go.Figure()

                # Giá trị mua theo mức giá - màu xanh lá
                fig9.add_trace(go.Bar(
                    x=df_price_level['price'],
                    y=df_price_level['buy_value'],
                    name='Giá Trị Mua',
                    marker=dict(color='#2ECC71', line=dict(width=0)),
                ))

                # Giá trị bán theo mức giá - màu cam
                fig9.add_trace(go.Bar(
                    x=df_price_level['price'],
                    y=-df_price_level['sell_value'],  # Dùng dấu âm để hiển thị dưới trục
                    name='Giá Trị Bán',
                    marker=dict(color='#E74C3C', line=dict(width=0)),
                ))

                # Giá trị ròng theo mức giá - đường màu vàng
                fig9.add_trace(go.Scatter(
                    x=df_price_level['price'],
                    y=df_price_level['net_value'],
                    mode='lines+markers',
                    name='Net Value',
                    line=dict(color='#9B59B6', width=2, dash='dot'),
                    marker=dict(color='#9B59B6', size=6, symbol='circle')  # Dot với đường tròn
                ))

                # Cập nhật layout cho biểu đồ Giá trị
                fig9.update_layout(
                    title="📊 Giá Trị Mua, Bán và Giá Trị Ròng theo Mức Giá",
                    xaxis_title="Mức Giá (VND)",
                    yaxis_title="Giá Trị (VND)",
                    template='plotly_dark',
                    hovermode='x unified',
                    barmode='relative',
                    legend=dict(orientation='h', yanchor='bottom', y=1.02, xanchor='right', x=1)
                )

                # Hiển thị biểu đồ Giá trị
                st.plotly_chart(fig9, use_container_width=True)                

        except Exception as e:
            st.error(f"Đã xảy ra lỗi: {str(e)}")        

# ==== TAB 2 ====
with tab2:
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
            
            # Tính volume mua/bán lũy kế
            df_min['cumulative_volume_buy'] = df_min['volume_buy'].cumsum()
            df_min['cumulative_volume_sell'] = df_min['volume_sell'].cumsum()
            df_min['cumulative_volume_net'] = df_min['net'].cumsum()

            # Tính dòng tiền lũy kế
            df_min['cumulative_net'] = df_min['cumulative_value_buy'] - df_min['cumulative_value_sell']

            # Lấy các dòng tiền lũy kế cuối cùng
            cumulative_buy = df_min['cumulative_value_buy'].iloc[-1] if not df_min.empty else 0
            cumulative_sell = df_min['cumulative_value_sell'].iloc[-1] if not df_min.empty else 0
            cumulative_net = df_min['cumulative_net'].iloc[-1] if not df_min.empty else 0
            cumulative_volume_buy = df_min['cumulative_volume_buy'].iloc[-1] if not df_min.empty else 0
            cumulative_volume_sell = df_min['cumulative_volume_sell'].iloc[-1] if not df_min.empty else 0
            cumulative_volume_net = df_min['cumulative_volume_net'].iloc[-1] if not df_min.empty else 0


            return {
                "symbol": symbol,
                "cumulative_value_buy": cumulative_buy,
                "cumulative_value_sell": cumulative_sell,
                "cumulative_value_net": cumulative_net,
                "cumulative_volume_buy": cumulative_volume_buy,
                "cumulative_volume_sell": cumulative_volume_sell,
                "cumulative_volume_net": cumulative_volume_net  # Thêm vào cột volume ròng lũy kế
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
        'VN30': ['ACB','BCM','BID','BVH','CTG',	'FPT','GAS','GVR','HDB','HPG',	'LPB','MBB','MSN', 'MWG', 'PLX','SAB','SHB','SSB','SSI','STB','TCB','TPB','VCB','VHM','VIB','VIC', 'VJC','VNM','VPB','VRE'],
        'Ngân hàng': ['ACB', 'BID', 'CTG', 'EIB', 'MBB', 'NVB', 'SHB', 'STB', 'VCB', 'VIB', 'LPB', 'TPB', 'OCB', 'SSB', 'HDB', 'TCB', 'VPB'],
        'Chứng khoán': ['AGR', 'ART', 'BSI', 'BVS', 'CTS', 'FTS', 'HCM', 'MBS', 'SBS', 'SHS', 'SSI', 'TVB', 'TVS', 'VCI', 'VDS', 'VIX', 'VND'],
        'Thép': ['HPG', 'HSG', 'NKG', 'POM', 'SHA', 'TIS', 'TVN', 'VGS', 'HMC', 'SHI', 'SMC', 'TLH'],
        'Bất động sản': ['IJC', 'LDG', 'NVT', 'AMD', 'C21', 'CEO', 'D2D', 'DIG', 'DRH', 'DXG', 'FLC', 'HAR', 'HDC', 'HDG', 'HLD', 'HQC', 'ITC', 'KDH', 'NBB', 'NDN', 'NLG', 'NTL', 'NVL', 'PDR', 'QCG', 'SCR', 'SJS', 'TDH', 'TIG', 'VIC', 'VPH', 'IDV', 'ITA', 'KBC', 'LHG', 'VC3', 'LGL'],
        'Công nghệ': ['CMG', 'SGT', 'ITD', 'VEC', 'FPT', 'ELC', 'ABC'],
        'Bán lẻ': ['MSN', 'MWG', 'DGW', 'PNJ', 'FRT'],
        'Điện nước': ['BWE', 'VCW', 'DQC', 'GDT', 'RAL', 'CHP', 'NT2', 'PPC', 'SBA', 'SJD', 'VSH'],
        'Dầu khí': ['PVB', 'PVC', 'PVD', 'PVS', 'ASP', 'CNG', 'GAS', 'PGC', 'PGS', 'PLX', 'PVG', 'PVO'],
        'Xây dựng': ['C32', 'C47', 'CII', 'CTD', 'CTI', 'FCN', 'HBC', 'HC3', 'HTI', 'HUT', 'L14', 'MCG', 'LCG', 'PC1', 'DPG', 'PHC', 'PVX', 'PXS', 'SD5', 'SD6', 'SD9', 'TCD', 'UIC', 'VCG', 'VMC', 'VNE', 'THG', 'VPD', 'TV2'],
        'Đầu tư công': ['HHV', 'LCG', 'HTI', 'DPG', 'EVG'],
        'Thực phẩm': ['MSN', 'TNA', 'VNM', 'LSS', 'QNS', 'SBT', 'MCH', 'VOC', 'NAF', 'SCD', 'SAB', 'SMB', 'KDC'],
        'Bảo hiểm': ['VNR', 'ABI', 'BIC', 'BMI', 'MIG', 'PGI', 'PVI', 'BVH'],
        'Thủy sản': ['ANV', 'ASM', 'FMC', 'HVG', 'IDI', 'SSN', 'VHC'],
        'Dệt may': ['ADS', 'EVE', 'FTM', 'GMC', 'HTG', 'KMR', 'STK', 'TCM', 'TNG', 'TVT', 'VGG', 'VGT'],
        'Cao su': ['DPR', 'DRI', 'HRC', 'PHR', 'TRC'],
        'Dược phẩm': ['DCL', 'DHG', 'DHT', 'IMP', 'TRA', 'DVN', 'DBD'],
        'Vận tải': ['PVT', 'GSP', 'SWC', 'VIP', 'VOS', 'VTO', 'SKG', 'SRT', 'VNS', 'SAS'],
        'Cảng biển': ['HAH', 'STG', 'GMD', 'PDN', 'PHP', 'SGP', 'VSC'],
        'Nhựa': ['AAA', 'BMP', 'DAG', 'DNP', 'NTP', 'RDP'],
        'Khu CN': ['KBC', 'SZC', 'TIP', 'BCM', 'VGC', 'IDC'],
        'Phân bón': ['HAI', 'LTG', 'TSC', 'VFG', 'BFC', 'DCM', 'DDV', 'DPM', 'LAS', 'QBS', 'SFG', 'CSM', 'DRC', 'SRC', 'CSV', 'DGC', 'PLC', 'LIX', 'NET']
        # Add other sectors as required...
    }

    selected_sector = st.selectbox('Chọn nhóm ngành:', options=list(sector_map.keys()), index=0, key="sector_select")

    # Select a date for analysis
    selected_date = st.date_input('Chọn ngày giao dịch:', value=date.today(), key='date')
    
    # --- Chọn thời gian refresh ---
    #col1, col2 = st.columns([1, 2])
    #with col1:
        #auto_refresh = st.checkbox("🔄 Tự động refresh")
    #with col2:
        #refresh_interval = st.slider("⏱ Thời gian refresh (giây):", min_value=30, max_value=600, value=60)

    # --- Thực hiện auto refresh ---
    #if auto_refresh:
        #st.markdown(f"<p style='color:green;'>Tự động làm mới sau mỗi {refresh_interval} giây...</p>", unsafe_allow_html=True)
        #time.sleep(refresh_interval)
        #st.rerun()

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
                for col in ['cumulative_value_buy', 'cumulative_value_sell', 'cumulative_value_net', 'cumulative_volume_buy', 'cumulative_volume_sell', 'cumulative_volume_net']:
                    df_display[col] = df_display[col].map(lambda x: f"{x:,.0f}".replace(",", "."))

                st.subheader("📋 Bảng Dòng Tiền Lũy Kế")
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
                    
                # Kết hợp top 10 mã dòng tiền ròng lớn nhất và nhỏ nhất
                top_10_positive = df_symbols.nlargest(10, 'cumulative_value_net')
                top_10_negative = df_symbols.nsmallest(10, 'cumulative_value_net')
                combined = pd.concat([top_10_positive, top_10_negative])
                combined = combined.drop_duplicates(subset='symbol')

                # Sắp xếp theo dòng tiền ròng giảm dần để biểu đồ dễ đọc
                combined_sorted = combined.sort_values(by='cumulative_value_net', ascending=False)

                # Tạo biểu đồ cột
                fig = go.Figure()

                fig.add_trace(go.Bar(
                    x=combined_sorted['symbol'],
                    y=combined_sorted['cumulative_value_net'],
                    marker_color=['#2ECC71' if val >= 0 else '#E74C3C' for val in combined_sorted['cumulative_value_net']],
                    text=[format_number(x) for x in combined_sorted['cumulative_value_net']],  # Sử dụng hàm định dạng số
                    textposition='auto',
                    name='Dòng tiền ròng'
                ))

                fig.update_layout(
                    title="💰 Top 10 Dòng Tiền Ròng Lớn Nhất và Nhỏ Nhất",
                    xaxis_title="Mã cổ phiếu",
                    yaxis_title="Dòng tiền ròng (VND)",
                    plot_bgcolor='rgba(0,0,0,0)',
                    paper_bgcolor='rgba(0,0,0,0)',
                    height=500
                )

                st.plotly_chart(fig, use_container_width=True)
                
                # ===== BIỂU ĐỒ DÒNG TIỀN LŨY KẾ NHÓM =====
                st.subheader("📈 Biểu Đồ Dòng Tiền Lũy Kế Nhóm Ngành")

                # Sắp xếp để biểu đồ đẹp hơn
                df_symbols_sorted = df_symbols.sort_values(by='cumulative_value_net', ascending=False)

                fig_group = go.Figure()

                # Thêm cột mua lũy kế
                fig_group.add_trace(go.Bar(
                    x=df_symbols_sorted['symbol'],
                    y=df_symbols_sorted['cumulative_value_buy'],
                    name='Mua lũy kế',
                    marker_color='#2ECC71'
                ))

                # Thêm cột bán lũy kế
                fig_group.add_trace(go.Bar(
                    x=df_symbols_sorted['symbol'],
                    y=df_symbols_sorted['cumulative_value_sell'],
                    name='Bán lũy kế',
                    marker_color='#E74C3C'
                ))

                # Thêm đường dòng tiền ròng lũy kế
                fig_group.add_trace(go.Scatter(
                    x=df_symbols_sorted['symbol'],
                    y=df_symbols_sorted['cumulative_value_net'],
                    name='Ròng lũy kế',
                    mode='lines+markers',
                    line=dict(color='#9B59B6', width=3)
                ))

                fig_group.update_layout(
                    barmode='group',
                    title='💼 Dòng Tiền Lũy Kế Theo Nhóm Cổ Phiếu',
                    xaxis_title='Mã cổ phiếu',
                    yaxis_title='Giá trị (VND)',
                    plot_bgcolor='rgba(0,0,0,0)',
                    paper_bgcolor='rgba(0,0,0,0)',
                    height=550,
                    legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
                )

                st.plotly_chart(fig_group, use_container_width=True)


            else:
                st.warning("Không thể phân tích dòng tiền các mã cổ phiếu này.")
        else:
            st.warning("Không có mã cổ phiếu nào để phân tích.")

          
# ==== TAB 3 ====            
with tab3:
    st.title("📊 Biểu Đồ Nến Nhật – Giá Cổ Phiếu")

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
                df_candle['time'] = pd.to_datetime(df_candle['time'])  # GIỮ nguyên datetime
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
                
                # Tính toán các thay đổi
                df_candle['delta_price'] = df_candle['close'] - df_candle['open']
                df_candle['delta_volume'] = df_candle['volume'].diff()
                # Tính phần trăm thay đổi theo ngày
                df_candle = df_candle.sort_values('time')
                df_candle['pct_change_price'] = df_candle['close'].pct_change() * 100
                df_candle['pct_change_volume'] = df_candle['volume'].pct_change() * 100

                # Làm tròn 2 chữ số
                df_candle['pct_change_price'] = df_candle['pct_change_price'].round(2)
                df_candle['pct_change_volume'] = df_candle['pct_change_volume'].round(2)

                # Lọc dữ liệu 30 và 90 ngày gần nhất
                latest_time = df_candle['time'].max()
                df_box_30 = df_candle[df_candle['time'] >= latest_time - timedelta(days=30)].copy()
                df_box_90 = df_candle[df_candle['time'] >= latest_time - timedelta(days=90)].copy()

                # ✅ Cột thời gian hiển thị để dùng trong biểu đồ (dạng chuỗi ngắn gọn)
                df_candle['time_str'] = df_candle['time'].dt.strftime('%d-%m')

                # Tính các đường MA
                df_candle['MA5'] = df_candle['close'].rolling(window=5).mean()
                df_candle['MA20'] = df_candle['close'].rolling(window=20).mean()
                df_candle['MA50'] = df_candle['close'].rolling(window=50).mean()

                fig = go.Figure(data=[go.Candlestick(
                    x=df_candle['time_str'],
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
                        x=df_candle['time_str'],
                        y=df_candle['MA5'],
                        mode='lines',
                        name='MA 5',
                        line=dict(color='blue', width=2)
                    ))

                if show_ma20:
                    fig.add_trace(go.Scatter(
                        x=df_candle['time_str'],
                        y=df_candle['MA20'],
                        mode='lines',
                        name='MA 20',
                        line=dict(color='orange', width=2)
                    ))

                if show_ma50:
                    fig.add_trace(go.Scatter(
                        x=df_candle['time_str'],
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
                        tickvals=df_candle['time_str'],  # Hiển thị các giá trị có dữ liệu
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
                    x=df_candle['time_str'],
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
                        tickvals=df_candle['time_str'],  # Hiển thị các giá trị có dữ liệu
                        tickangle=45  # Góc quay các nhãn để tránh chồng chéo
                    ),
                    yaxis=dict(
                        showgrid=False,
                        zeroline=False
                    )
                )

                # Hiển thị biểu đồ khối lượng
                st.plotly_chart(fig_volume, use_container_width=True)
                
                
                ##✅ Vẽ biểu đồ tương quan có yếu tố thời gian
                # Giới hạn dữ liệu trong 30 ngày gần nhất
                last_30_days = df_candle['time'].max() - timedelta(days=30)
                # Sắp xếp theo thời gian giảm dần và lấy 30 dòng gần nhất
                df_corr = df_candle.sort_values("time", ascending=False).head(30).sort_values("time")
                
                
                
                # ✅ Vẽ biểu đồ tương quan có yếu tố thời gian
                fig_corr = px.scatter(
                    df_corr,
                    x="close",
                    y="volume",
                    color="time",  # thời gian thể hiện bằng màu
                    labels={"close": "Giá đóng cửa", "volume": "Khối lượng", "time": "Thời gian"},
                    title="Tương quan giữa Giá đóng cửa và Khối lượng (30 ngày gần nhất)",
                    trendline="ols"
                )
                st.plotly_chart(fig_corr, use_container_width=True)   


                # Biểu đồ line giá & khối lượng 
                # ✅ Biểu đồ line với cả close và volume (2 y-axis)
                fig_line = go.Figure()

                # Line 1: Giá đóng cửa (close)
                fig_line.add_trace(go.Scatter(
                    x=df_candle['time_str'],
                    y=df_candle['close'],
                    mode='lines+markers',
                    name='Giá đóng cửa',
                    line=dict(color='blue'),
                    yaxis='y1'
                ))

                # Line 2: Khối lượng (volume) trên trục y thứ 2
                fig_line.add_trace(go.Scatter(
                    x=df_candle['time_str'],
                    y=df_candle['volume'],
                    mode='lines+markers',
                    name='Khối lượng',
                    line=dict(color='orange'),
                    yaxis='y2'
                ))

                fig_line.update_layout(
                    title='Biểu đồ Giá và Khối lượng theo Thời gian',
                    xaxis=dict(title='Ngày', type='category', tickangle=45),
                    yaxis=dict(
                        title='Giá đóng cửa',
                        showgrid=False
                    ),
                    yaxis2=dict(
                        title='Khối lượng',
                        overlaying='y',
                        side='right',
                        showgrid=False
                    ),
                    legend=dict(x=0.01, y=0.99),
                    height=400,
                    margin=dict(l=0, r=0, t=40, b=0)
                )

                st.plotly_chart(fig_line, use_container_width=True)
                
                #✅ Boxplot cho 30 và 90 ngày
                # Tạo biến ngày giới hạn
                max_date = df_candle['time'].max()
                min_date_30 = max_date - pd.Timedelta(days=30)
                min_date_90 = max_date - pd.Timedelta(days=90)

                # Lọc dữ liệu
                df_30 = df_candle[(df_candle['time'] >= min_date_30) & (df_candle['time'] <= max_date)].copy()
                df_90 = df_candle[(df_candle['time'] >= min_date_90) & (df_candle['time'] <= max_date)].copy()

                # Kiểm tra dữ liệu không rỗng
                if not df_30.empty and not df_90.empty:
                    # Boxplot cho 30 ngày
                    fig_box_30 = make_subplots(rows=1, cols=2, subplot_titles=(
                        "📦 Biến động giá (%) – 30 ngày", "📦 Biến động khối lượng (%) – 30 ngày"))

                    fig_box_30.add_trace(go.Box(
                        y=df_30['pct_change_price'],
                        boxpoints='outliers',
                        name="Giá",
                        marker_color='green'
                    ), row=1, col=1)

                    fig_box_30.add_trace(go.Box(
                        y=df_30['pct_change_volume'],
                        boxpoints='outliers',
                        name="Khối lượng",
                        marker_color='orange'
                    ), row=1, col=2)

                    fig_box_30.update_layout(
                        title_text=f"Biến động theo ngày trong 30 ngày gần nhất – {symbol}",
                        height=500,
                        template='plotly_white'
                    )

                    st.plotly_chart(fig_box_30, use_container_width=True)

                    # Boxplot cho 90 ngày
                    fig_box_90 = make_subplots(rows=1, cols=2, subplot_titles=(
                        "📦 Biến động giá (%) – 90 ngày", "📦 Biến động khối lượng (%) – 90 ngày"))

                    fig_box_90.add_trace(go.Box(
                        y=df_90['pct_change_price'],
                        boxpoints='outliers',
                        name="Giá",
                        marker_color='blue'
                    ), row=1, col=1)

                    fig_box_90.add_trace(go.Box(
                        y=df_90['pct_change_volume'],
                        boxpoints='outliers',
                        name="Khối lượng",
                        marker_color='red'
                    ), row=1, col=2)

                    fig_box_90.update_layout(
                        title_text=f"Biến động theo ngày trong 90 ngày gần nhất – {symbol}",
                        height=500,
                        template='plotly_white'
                    )

                    st.plotly_chart(fig_box_90, use_container_width=True)
                else:
                    st.warning("Không đủ dữ liệu để tạo boxplot cho 30 hoặc 90 ngày.")        
                

                st.download_button(
                    label="📥 Tải dữ liệu giá lịch sử (.CSV)",
                    data=df_candle.to_csv(index=False).encode("utf-8"),
                    file_name=f"{symbol}_gia_lich_su_{timeframe}.csv",
                    mime="text/csv"
                )

        except Exception as e:
            st.error(f"Đã xảy ra lỗi: {e}")

# ==== TAB 4 ====  
with tab4:
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
          


with tab6:
    st.title("💹 Phân tích thị trường")

    st.markdown("Chọn nhóm ngành để phân tích dữ liệu biến động của ngành.")
    # Dropdown cho tab6 và tab7
    selected_dropdown = st.selectbox("Chọn chức năng", ["Phân tích thị trường (realtime)", "Phân tích thị trường (offline)"])

    if selected_dropdown == "Phân tích thị trường (realtime)":
    # ==== TAB 6 ====
        with st.expander("💹 Phân tích biến động nhóm ngành", expanded=True):
            st.title("💹 Phân tích biến động nhóm ngành")
            st.markdown("Chọn nhóm ngành và ngày để xem biểu đồ giá trị giao dịch của các cổ phiếu.")      
            

            # Chọn nhóm ngành từ dropdown
            selected_sector = st.selectbox('Chọn nhóm ngành:', options=list(sector_map.keys()), index=0, key="sector_select_1_unique")

            # Chọn ngày
            selected_date = st.date_input("Chọn ngày", value=date.today(), key="date_input_1_unique")

            # Lấy danh sách mã cổ phiếu theo nhóm ngành đã chọn
            stock_symbols = sector_map.get(selected_sector, [])

            if st.button("💹 Phân tích"):
                try:
                    # Khởi tạo đối tượng Vnstock
                    vn = Vnstock()

                    df_list = []
                    for symbol in stock_symbols:
                        stock = vn.stock(symbol=symbol, source='VCI')
                        df = stock.quote.history(start='2020-01-01', end=str(selected_date))
                        if df is not None and not df.empty:
                            df['symbol'] = symbol
                            df_list.append(df)

                    df_all = pd.concat(df_list, ignore_index=True)
                    df_all['time'] = pd.to_datetime(df_all['time'])

                    # Lọc ra các dòng dữ liệu trước hoặc bằng ngày được chọn
                    df_filtered = df_all[df_all['time'] <= pd.to_datetime(selected_date)]

                    # Lấy 2 dòng gần nhất (ngày được chọn và ngày trước đó) cho mỗi mã
                    df_latest = df_filtered.sort_values(['symbol', 'time']).groupby('symbol').tail(2)

                    # Tính close_previous
                    df_latest = df_latest.sort_values(['symbol', 'time'])
                    df_latest['close_previous'] = df_latest.groupby('symbol')['close'].shift(1)

                    # Tính thay đổi
                    df_latest['change'] = df_latest['close'] - df_latest['close_previous']
                    df_latest['change_pct'] = ((df_latest['change'] / df_latest['close_previous']) * 100).round(2)
                    df_latest['color'] = df_latest['change'].apply(
                        lambda x: 'green' if x > 0 else ('red' if x < 0 else 'yellow')
                    )

                    # Chỉ lấy dòng mới nhất để vẽ treemap
                    df_latest = df_latest.groupby('symbol').tail(1)

                    # Chuẩn bị dữ liệu vẽ treemap
                    treemap_data = df_latest[['symbol', 'color', 'close', 'change_pct', 'volume']]
                    
                    # Định dạng giá trị hiển thị
                    treemap_data['close_formatted'] = treemap_data['close'].apply(lambda x: f"{x:.2f}")
                    treemap_data['volume_formatted'] = treemap_data['volume'].apply(lambda x: f"{x:,.0f}")

                    # Tạo biểu đồ Treemap
                    fig = go.Figure(go.Treemap(
                        labels=treemap_data['symbol'],
                        parents=[''] * len(treemap_data),
                        values=treemap_data['volume'],
                        
                        text=treemap_data['change_pct'].apply(lambda x: f"({x:.2f}%)"),  # Phần trăm thay đổi trong ô
                        textinfo="label+text",
                        textfont=dict(color='white', size=16),

                        customdata=treemap_data[['change_pct', 'close_formatted', 'volume_formatted']].values,

                        hovertemplate=(
                            "<b>%{label}</b><br>"
                            "Thay đổi: (%{customdata[0]:.2f}%)<br>"
                            "Giá đóng cửa: %{customdata[1]}<br>"
                            "Khối lượng: %{customdata[2]}<br>"
                            "<extra></extra>"
                        ),

                        marker=dict(
                            colors=treemap_data['color'].apply(
                                lambda x: '#2ECC71' if x == 'green' else ('#E74C3C' if x == 'red' else '#F1C40F')
                            )
                        )
                    ))

                    fig.update_layout(
                        title=f"Biểu đồ Treemap – Ngành: {selected_sector} | Ngày: {selected_date}",
                        margin=dict(t=50, l=25, r=25, b=25)
                    )

                    st.plotly_chart(fig, use_container_width=True)
                    
                    st.subheader("📊 Phân Tích Chuyên Sâu Theo Ngành")
                                           
                    #1: So sánh % thay đổi giữa các cổ phiếu trong ngành
                    fig_bar = px.bar(
                        df_latest.sort_values("change_pct", ascending=False),
                        x="symbol",
                        y="change_pct",
                        color="change_pct",
                        color_continuous_scale=["red", "yellow", "green"],
                        title=f"So sánh % thay đổi giữa các cổ phiếu – {selected_sector}",
                        labels={"change_pct": "% thay đổi"}
                    )
                    fig_bar.update_layout(template="plotly_white")
                    st.plotly_chart(fig_bar, use_container_width=True)
                    
                    #2: Khối lượng giao dịch so với % thay đổi
                    fig_scatter = px.scatter(
                        df_latest,
                        x="change_pct",
                        y="volume",
                        size="close",
                        color="change_pct",
                        color_continuous_scale="RdYlGn",
                        hover_name="symbol",
                        title=f"Khối lượng giao dịch vs % thay đổi – {selected_sector}",
                        labels={"change_pct": "% thay đổi", "volume": "Khối lượng"}
                    )
                    fig_scatter.update_layout(template="plotly_white")
                    st.plotly_chart(fig_scatter, use_container_width=True)
                    
                    #3: Xu hướng giá top 5
                    # Lấy 5 mã có volume cao nhất
                    top_symbols = df_latest.sort_values("volume", ascending=False).head(5)['symbol'].tolist()
                    df_top = df_all[df_all['symbol'].isin(top_symbols)]

                    fig_line = px.line(
                        df_top,
                        x="time",
                        y="close",
                        color="symbol",
                        title=f"Xu hướng giá – Top 5 mã theo khối lượng ({selected_sector})",
                        labels={"close": "Giá đóng cửa", "time": "Thời gian"}
                    )
                    fig_line.update_layout(template="plotly_white")
                    st.plotly_chart(fig_line, use_container_width=True)
                    
                    # ==== PHÂN TÍCH BOX PLOT – BIẾN ĐỘNG GIÁ ====

                    # Cố định khoảng thời gian: 30 ngày gần nhất trước selected_date
                    max_date = pd.to_datetime(selected_date)
                    min_date_30 = max_date - pd.Timedelta(days=30)

                    # Lọc dữ liệu theo thời gian cho 30 ngày
                    df_boxplot_30 = df_all[(df_all['time'] >= min_date_30) & (df_all['time'] <= max_date)].copy()

                    # Tính phần trăm thay đổi giá (%) cho 30 ngày
                    df_boxplot_30 = df_boxplot_30.sort_values(['symbol', 'time'])
                    df_boxplot_30['pct_change'] = df_boxplot_30.groupby('symbol')['close'].pct_change() * 100

                    # Làm tròn phần trăm thay đổi giá về 2 chữ số thập phân
                    df_boxplot_30['pct_change'] = df_boxplot_30['pct_change'].round(2)

                    # Loại bỏ các dòng không có dữ liệu
                    df_boxplot_30_clean = df_boxplot_30.dropna(subset=['pct_change'])

                    # Hiển thị Boxplot cho 30 ngày
                    if df_boxplot_30_clean.empty:
                        st.warning("Không có đủ dữ liệu để hiển thị biểu đồ cho 30 ngày.")
                    else:
                        fig_box_30 = px.box(
                            df_boxplot_30_clean,
                            x='symbol',
                            y='pct_change',
                            color='symbol',  # Mỗi mã cổ phiếu một màu
                            points="outliers",
                            title="📦 Boxplot – Biến động giá (%) trong 30 ngày gần nhất",
                            template="seaborn",  # Giao diện đẹp mắt hơn
                            color_discrete_sequence=px.colors.qualitative.Set2  # Bảng màu nhẹ nhàng
                        )

                        fig_box_30.update_layout(
                            xaxis_title="Mã cổ phiếu",
                            yaxis_title="% Thay đổi giá theo ngày",
                            height=600,
                            title_font_size=22,
                            title_x=0.0,  # Căn giữa tiêu đề
                            font=dict(size=14),
                            showlegend=False  # Ẩn chú thích nếu không cần
                        )

                        st.plotly_chart(fig_box_30, use_container_width=True)


                    # Cố định khoảng thời gian: 90 ngày gần nhất trước selected_date
                    min_date_90 = max_date - pd.Timedelta(days=90)

                    # Lọc dữ liệu theo thời gian cho 90 ngày
                    df_boxplot_90 = df_all[(df_all['time'] >= min_date_90) & (df_all['time'] <= max_date)].copy()

                    # Tính phần trăm thay đổi giá (%) cho 90 ngày
                    df_boxplot_90 = df_boxplot_90.sort_values(['symbol', 'time'])
                    df_boxplot_90['pct_change'] = df_boxplot_90.groupby('symbol')['close'].pct_change() * 100

                    # Làm tròn phần trăm thay đổi giá về 2 chữ số thập phân
                    df_boxplot_90['pct_change'] = df_boxplot_90['pct_change'].round(2)

                    # Loại bỏ các dòng không có dữ liệu
                    df_boxplot_90_clean = df_boxplot_90.dropna(subset=['pct_change'])

                    # Hiển thị Boxplot cho 90 ngày
                    if df_boxplot_90_clean.empty:
                        st.warning("Không có đủ dữ liệu để hiển thị biểu đồ cho 90 ngày.")
                    else:
                        fig_box_90 = px.box(
                            df_boxplot_90_clean,
                            x='symbol',
                            y='pct_change',
                            color='symbol',
                            points="outliers",
                            title="📦 Boxplot – Biến động giá (%) trong 90 ngày gần nhất",
                            template="seaborn",
                            color_discrete_sequence=px.colors.qualitative.Set2
                        )

                        fig_box_90.update_layout(
                            xaxis_title="Mã cổ phiếu",
                            yaxis_title="% Thay đổi giá theo ngày",
                            height=600,
                            title_font_size=22,
                            title_x=0.0,
                            font=dict(size=14),
                            showlegend=False
                        )

                        st.plotly_chart(fig_box_90, use_container_width=True)
                        
                    
                    #4: Ma trận tương quan giữa các cổ phiếu trong ngành    
                    # Tính toán % thay đổi giá hàng ngày
                    df_all = df_all.sort_values(['symbol', 'time'])
                    df_all['pct_change'] = df_all.groupby('symbol')['close'].pct_change() * 100
                    # Tính SMA 5 ngày
                    df_all['SMA_5'] = df_all.groupby('symbol')['close'].transform(lambda x: x.rolling(window=5).mean())

                    # Tính EMA 5 ngày
                    df_all['EMA_5'] = df_all.groupby('symbol')['close'].transform(lambda x: x.ewm(span=5, adjust=False).mean())

                    # Tính phần trăm thay đổi giá dựa trên SMA hoặc EMA
                    df_all['pct_change_SMA'] = df_all.groupby('symbol')['SMA_5'].pct_change() * 100
                    df_all['pct_change_EMA'] = df_all.groupby('symbol')['EMA_5'].pct_change() * 100

                    # Pivot để tạo ma trận symbol x date
                    df_pct_matrix = df_all.pivot_table(
                        index='time', columns='symbol', values='pct_change_SMA'
                    )

                    # Tính ma trận tương quan
                    corr_matrix = df_pct_matrix.corr()
                    
                    # Kiểm tra nếu số lượng mã < 2 thì không cần vẽ
                    if len(corr_matrix.columns) < 2:
                        st.warning("Không đủ dữ liệu để vẽ ma trận tương quan.")
                    else:
                        # Tính số mã để đặt kích thước phù hợp
                        n_symbols = len(corr_matrix.columns)
                        cell_size = 50  # pixels per cell

                        fig_corr = px.imshow(
                            corr_matrix,
                            text_auto=".2f",
                            color_continuous_scale='RdBu_r',
                            title=f"Ma trận tương quan phần trăm thay đổi giá theo SMA 5 ngày – {selected_sector}",
                            labels=dict(color="Hệ số tương quan")
                        )

                        fig_corr.update_layout(
                            xaxis_title="Mã cổ phiếu",
                            yaxis_title="Mã cổ phiếu",
                            title_font=dict(size=22),
                            font=dict(size=14),
                            width=max(700, cell_size * n_symbols),   # chiều rộng tối thiểu 700
                            height=max(700, cell_size * n_symbols),  # chiều cao tương đương
                            margin=dict(t=80, l=50, r=50, b=50),
                            template="plotly_white"
                        )

                        fig_corr.update_traces(
                            textfont=dict(size=14)
                        )

                        st.plotly_chart(fig_corr, use_container_width=True)
                        
                except Exception as e:
                    st.error(f"Đã xảy ra lỗi: {e}")   
                    
    # ==== TAB 7 ====            
    elif selected_dropdown == "Treemap realtime":
        with st.expander("💹 Treemap realtime", expanded=True):
            st.title("💹 Treemap – Giá Cổ Phiếu Theo Ngành (Realtime)")
            st.markdown("Chọn nhóm ngành và ngày để xem biểu đồ giá trị giao dịch của các cổ phiếu.")

            selected_sector = st.selectbox('Chọn nhóm ngành:', options=list(sector_map.keys()), index=0, key="sector_select_2_unique")
            selected_date = st.date_input("Chọn ngày", value=date.today(), key="date_input_2_unique")
            stock_symbols = sector_map.get(selected_sector, [])

            if st.button("💹 Hiển thị"):
                try:
                    vn = Vnstock()
                    df_hist_list = []
                    df_realtime_list = []

                    for symbol in stock_symbols:
                        stock = vn.stock(symbol=symbol, source='VCI')

                        # Dữ liệu lịch sử để lấy giá hôm trước
                        df_hist = stock.quote.history(start='2020-01-01', end=str(selected_date))
                        if df_hist is not None and not df_hist.empty:
                            df_hist['symbol'] = symbol
                            df_hist_list.append(df_hist)

                        # Dữ liệu realtime để lấy giá cuối cùng và volume lũy kế
                        df_intraday = stock.quote.intraday(symbol=symbol, page_size=10000)
                        if df_intraday is not None and not df_intraday.empty:
                            df_intraday['symbol'] = symbol
                            last_price = df_intraday.iloc[-1]['price']
                            total_volume = df_intraday['volume'].sum()
                            df_realtime_list.append({
                                'symbol': symbol,
                                'last_price': last_price,
                                'volume': total_volume
                            })

                    # Tổng hợp dữ liệu realtime
                    df_realtime = pd.DataFrame(df_realtime_list)

                    # Tính giá hôm trước từ dữ liệu lịch sử
                    df_all = pd.concat(df_hist_list, ignore_index=True)
                    df_all['time'] = pd.to_datetime(df_all['time'])
                    df_filtered = df_all[df_all['time'] <= pd.to_datetime(selected_date)]
                    df_latest = df_filtered.sort_values(['symbol', 'time']).groupby('symbol').tail(2)
                    df_latest = df_latest.sort_values(['symbol', 'time'])
                    df_latest['close_previous'] = df_latest.groupby('symbol')['close'].shift(1)
                    df_previous = df_latest.groupby('symbol').tail(1)[['symbol', 'close_previous']]

                    # Gộp dữ liệu realtime và close_previous
                    df_merged = pd.merge(df_realtime, df_previous, on='symbol', how='left')
                    df_merged['change'] = df_merged['last_price'] - df_merged['close_previous']
                    df_merged['change_pct'] = (df_merged['change'] / df_merged['close_previous']) * 100
                    df_merged['color'] = df_merged['change'].apply(
                        lambda x: 'green' if x > 0 else ('red' if x < 0 else 'yellow')
                    )

                    # Định dạng hiển thị
                    df_merged['close_formatted'] = df_merged['last_price'].apply(lambda x: f"{x:,.2f}")
                    df_merged['volume_formatted'] = df_merged['volume'].apply(lambda x: f"{x:,.0f}")
                    
                    # Chuẩn bị bảng hiển thị
                    df_merged_display = df_merged[['symbol', 'last_price', 'volume', 'close_previous', 'change', 'change_pct']]
                    df_merged_display.columns = ['Mã CP', 'Giá hiện tại', 'Khối lượng lũy kế', 'Giá hôm trước', 'Thay đổi', 'Thay đổi (%)']
                    df_merged_display['Giá hiện tại'] = df_merged_display['Giá hiện tại'].apply(lambda x: f"{x:,.2f}")
                    df_merged_display['Khối lượng lũy kế'] = df_merged_display['Khối lượng lũy kế'].apply(lambda x: f"{x:,.0f}")
                    df_merged_display['Giá hôm trước'] = df_merged_display['Giá hôm trước'].apply(lambda x: f"{x:,.2f}")
                    df_merged_display['Thay đổi'] = df_merged_display['Thay đổi'].apply(lambda x: f"{x:,.2f}")
                    df_merged_display['Thay đổi (%)'] = df_merged_display['Thay đổi (%)'].apply(lambda x: f"{x:.2f}%")

                    # Hiển thị bảng
                    #st.markdown("### 📋 Bảng dữ liệu chi tiết")
                    #st.dataframe(df_merged_display, use_container_width=True)

                    # Vẽ Treemap
                    fig = go.Figure(go.Treemap(
                        labels=df_merged['symbol'],
                        parents=[''] * len(df_merged),
                        values=df_merged['volume'],
                        text=df_merged['change_pct'].apply(lambda x: f"({x:.2f}%)"),
                        textinfo="label+text",
                        textfont=dict(color='white', size=16),
                        customdata=df_merged[['change_pct', 'close_formatted', 'volume_formatted']].values,
                        hovertemplate=(
                            "<b>%{label}</b><br>"
                            "Thay đổi: (%{customdata[0]:.2f}%)<br>"
                            "Giá hiện tại: %{customdata[1]}<br>"
                            "Khối lượng: %{customdata[2]}<br>"
                            "<extra></extra>"
                        ),
                        marker=dict(
                            colors=df_merged['color'].apply(
                                lambda x: '#2ECC71' if x == 'green' else ('#E74C3C' if x == 'red' else '#F1C40F')
                            )
                        )
                    ))

                    fig.update_layout(
                        title=f"Biểu đồ Treemap – Ngành: {selected_sector} | Ngày: {selected_date}",
                        margin=dict(t=50, l=25, r=25, b=25)
                    )

                    st.plotly_chart(fig, use_container_width=True)

                except Exception as e:
                    st.error(f"Đã xảy ra lỗi: {e}")
                
    if selected_dropdown == "Phân tích thị trường (offline)":
    # ==== TAB 8 ====
        # ==== Tạo Tab mới cho phân tích dữ liệu CSV với cột Industry ====
        
        # Tạo template CSV
        def create_csv_template():
            # Tạo một DataFrame mẫu với các cột cần thiết
            template_data = {
                'Ticker': [''],
                'Date/Time': [''],
                'Close': [0.0],
                'Change': [0.0],
                'Volume': [0]
            }
            
            df_template = pd.DataFrame(template_data)
            
            # Chuyển DataFrame thành CSV
            csv = df_template.to_csv(index=False, encoding='utf-8')
            return csv        
        
        # Tạo template thư viện nhóm ngành
        def create_industry_library_template():
            template_data = {
                'Ticker': [''],     # ví dụ mã cổ phiếu
                'Industry': ['']  # ví dụ nhóm ngành tương ứng
            }
            df_template = pd.DataFrame(template_data)
            csv = df_template.to_csv(index=False, encoding='utf-8')
            return csv
            
        # Tạo một nút tải về CSV
        csv_template = create_csv_template()
        # Tạo nút tải template thư viện nhóm ngành
        csv_industry_template = create_industry_library_template()        
            
        # ==== HIỂN THỊ HAI NÚT TẢI SONG SONG ====
        col1, col2 = st.columns(2)
        
        with col1:   
            # Nút tải về template CSV
            st.download_button(
                label="Tải template dữ liệu",
                data=csv_template,
                file_name="template.csv",
                mime="text/csv"
            )
            st.markdown("</div>", unsafe_allow_html=True)
        with col2:       
            st.download_button(
                label="📥 Tải template thư viện nhóm ngành",
                data=csv_industry_template,
                file_name="industry_library_template.csv",
                mime="text/csv"
            )
            st.markdown("</div>", unsafe_allow_html=True)
        
        # === 1. Tải lên thư viện nhóm ngành (upload & ghi đè nếu có) ===
        st.markdown("<h4>📁 Thư viện nhóm ngành</h4>", unsafe_allow_html=True)

        industry_file = st.file_uploader("Tải lên file thư viện nhóm ngành (CSV)", type=["csv"], key="industry_upload")

        if industry_file is not None:
            with open("industry_library.csv", "wb") as f:
                f.write(industry_file.read())
            st.success("✅ Thư viện nhóm ngành đã được cập nhật!")

        # Đọc thư viện nếu đã có
        if os.path.exists("industry_library.csv"):
            df_industry_library = pd.read_csv("industry_library.csv")
            last_update = pd.to_datetime(os.path.getmtime('industry_library.csv'), unit='s')
            st.markdown(f"<p style='font-size:18px; font-weight:500;'>📅 Thư viện được cập nhật lần cuối: {last_update.strftime('%d/%m/%Y %H:%M:%S')}</h5>", unsafe_allow_html=True)

        else:
            st.error("❌ Chưa có thư viện nhóm ngành. Vui lòng tải lên trước khi phân tích.")
            st.stop()


        # === 2. Tải lên file dữ liệu cổ phiếu ===
        # Tải file CSV chứa dữ liệu cổ phiếu
        st.markdown("<h4>📈 Phân tích Cổ Phiếu từ Dữ Liệu CSV (Theo Nhóm Ngành)</h4>", unsafe_allow_html=True)
        uploaded_file = st.file_uploader("Tải lên file CSV chứa dữ liệu cổ phiếu", type=["csv"])

        # Nếu có file mới được tải lên → lưu lại
        if uploaded_file is not None:
            with open("stock_data.csv", "wb") as f:
                f.write(uploaded_file.read())
            st.success("✅ Dữ liệu cổ phiếu đã được cập nhật!")

        # Nếu file đã tồn tại (từ upload hoặc đã có trước), thì xử lý tiếp
        if os.path.exists("stock_data.csv"):
            try:
                df = pd.read_csv("stock_data.csv")
            except Exception as e:
                st.error(f"❌ Lỗi khi đọc file CSV: {e}")
                st.stop()

            # Kiểm tra và hiển thị dữ liệu
            trading_date = pd.to_datetime(df['Date/Time'].iloc[0]).strftime("%d/%m/%Y")
            st.markdown(f"<p style='font-size:18px; font-weight:500;'>📅 Dữ liệu ngày {trading_date} đã tải lên</p>", unsafe_allow_html=True)
            st.dataframe(df.head())
            

            # Xử lý dữ liệu: chuyển đổi cột Date/Time sang định dạng ngày tháng
            df['Date/Time'] = pd.to_datetime(df['Date/Time'], format='%m/%d/%Y')

            # Cải thiện định dạng cột "close" và "Change" (làm tròn đến 2 chữ số thập phân)
            df['close'] = df['Close'].round(2)
            df['Change'] = df['Change'].round(2)
            
            
            # === Gắn nhóm ngành từ thư viện ===
            df = df.merge(df_industry_library, on='Ticker', how='left')

            st.subheader("🔍 Dữ liệu sau khi gắn nhóm ngành:")
            st.dataframe(df.head())

            # Kiểm tra mã chưa có ngành
            missing = df[df['Industry'].isna()]['Ticker'].unique()
            if len(missing) > 0:
                st.warning(f"⚠️ Có {len(missing)} mã chưa có nhóm ngành trong thư viện.")
                st.write(missing)

            # ==== Dropdown cho người dùng chọn Phân Tích Ngành hay Thị Trường ====
            analysis_options = ['Phân tích Thị Trường', 'Phân tích Ngành']
            selected_analysis = st.selectbox("Chọn loại phân tích", analysis_options)

            if selected_analysis == "Phân tích Ngành":
                # ==== Phân tích Ngành ====

                # Dropdown cho người dùng chọn nhóm ngành hoặc tất cả các mã
                industry_options = ['Tất cả'] + sorted(df['Industry'].dropna().unique().tolist())
                selected_industry = st.selectbox("Chọn nhóm ngành để phân tích", industry_options)

                # Lọc dữ liệu theo nhóm ngành được chọn
                if selected_industry != 'Tất cả':
                    df_filtered = df[df['Industry'] == selected_industry]
                else:
                    df_filtered = df

                # ==== Biểu đồ 1: Tree Map theo ngành ====
                st.subheader("🌳 Tree Map – Biến động giá và Khối lượng giao dịch")

                # Định nghĩa màu sắc dựa trên sự thay đổi giá
                df_filtered['color'] = df_filtered['Change'].apply(
                    lambda x: 'green' if x > 0 else ('red' if x < 0 else 'yellow')
                )

                # Tạo biểu đồ Treemap
                fig_tree = go.Figure(go.Treemap(
                    labels=df_filtered['Ticker'],  # Mã cổ phiếu
                    parents=[selected_industry] * len(df_filtered),  # Đặt nhóm ngành là cha mẹ
                    values=df_filtered['Volume'],  # Khối lượng giao dịch
                    text=df_filtered['Change'].apply(lambda x: f"({x:.2f}%)"),  # Phần trăm thay đổi
                    textinfo="label+text",  # Hiển thị nhãn và text
                    textfont=dict(color='white', size=16),  # Định dạng chữ

                    # Dữ liệu hiển thị khi hover
                    customdata=df_filtered[['Change', 'close', 'Volume']].values,
                    hovertemplate=(
                        "<b>%{label}</b><br>"
                        "Thay đổi: (%{customdata[0]:.2f}%)<br>"
                        "Giá đóng cửa: %{customdata[1]}<br>"
                        "Khối lượng: %{customdata[2]}<br>"
                        "<extra></extra>"
                    ),

                    # Màu sắc của các ô trong treemap
                    marker=dict(
                        colors=df_filtered['color'].apply(
                            lambda x: '#2ECC71' if x == 'green' else ('#E74C3C' if x == 'red' else '#F1C40F')
                        )
                    )
                ))

                # Cập nhật bố cục của biểu đồ
                fig_tree.update_layout(
                    title="🌳 Tree Map – Biến động giá và Khối lượng giao dịch",
                    margin=dict(t=50, l=25, r=25, b=25)
                )

                # Hiển thị biểu đồ
                st.plotly_chart(fig_tree, use_container_width=True)

                # ==== Biểu đồ 2: So sánh % thay đổi giữa các cổ phiếu trong ngành ====
                st.subheader(f"📊 So sánh % thay đổi giữa các cổ phiếu – {selected_industry}")

                # Loại bỏ các bản sao theo Ticker để đảm bảo không có cổ phiếu nào bị trùng
                df_filtered_unique = df_filtered.drop_duplicates(subset=["Ticker"])

                # Sắp xếp dữ liệu theo phần trăm thay đổi
                df_sorted = df_filtered_unique.sort_values("Change", ascending=False)

                # Nếu số lượng mã cổ phiếu lớn hơn 30, lấy 15 mã có % thay đổi lớn nhất và nhỏ nhất
                if len(df_sorted) > 30:
                    df_sorted = pd.concat([df_sorted.head(15), df_sorted.tail(15)])

                # Tạo biểu đồ thanh để so sánh % thay đổi giữa các cổ phiếu
                fig_bar = px.bar(
                    df_sorted,
                    x="Ticker",  # Mã cổ phiếu
                    y="Change",  # Phần trăm thay đổi
                    color="Change",  # Màu sắc dựa trên % thay đổi
                    color_continuous_scale=["red", "yellow", "green"],  # Màu sắc cho phần trăm thay đổi
                    title=f"So sánh % thay đổi giữa các cổ phiếu – {selected_industry}",
                    labels={"Change": "% thay đổi"}
                )

                # Cập nhật bố cục của biểu đồ
                fig_bar.update_layout(
                    template="plotly_white",
                    xaxis_title="Mã cổ phiếu",
                    yaxis_title="% Thay đổi giá",
                    height=500,
                    xaxis={'categoryorder': 'total descending'}  # Sắp xếp theo giá trị % thay đổi
                )

                # Hiển thị biểu đồ thanh
                st.plotly_chart(fig_bar, use_container_width=True)

                # ==== Biểu đồ 3: Khối lượng giao dịch vs % thay đổi ====
                st.subheader(f"📉 Khối lượng giao dịch vs % thay đổi – {selected_industry}")

                # Sắp xếp dữ liệu theo phần trăm thay đổi
                df_sorted = df_filtered.sort_values("Change", ascending=False)

                # Nếu số lượng mã cổ phiếu lớn hơn 30, lấy 15 mã có % thay đổi lớn nhất và 15 mã có % thay đổi nhỏ nhất
                if len(df_sorted) > 30:
                    df_sorted = pd.concat([df_sorted.head(15), df_sorted.tail(15)])

                # Tạo biểu đồ scatter: Khối lượng giao dịch so với % thay đổi
                fig_scatter = px.scatter(
                    df_sorted,
                    x="Change",  # Phần trăm thay đổi
                    y="Volume",  # Khối lượng giao dịch
                    size="close",  # Kích thước điểm biểu thị giá đóng cửa
                    color="Change",  # Màu sắc dựa trên % thay đổi
                    color_continuous_scale="RdYlGn",  # Chọn bảng màu đỏ - vàng - xanh
                    hover_name="Ticker",  # Hiển thị mã cổ phiếu khi hover
                    title=f"Khối lượng giao dịch vs % thay đổi – {selected_industry}",
                    labels={"Change": "% thay đổi", "Volume": "Khối lượng"}
                )

                # Cập nhật bố cục của biểu đồ
                fig_scatter.update_layout(
                    template="plotly_white",
                    xaxis_title="% Thay đổi",
                    yaxis_title="Khối lượng giao dịch",
                    height=500
                )

                # Hiển thị biểu đồ scatter
                st.plotly_chart(fig_scatter, use_container_width=True)  


                # ==== Biểu đồ 4: Biểu đồ phân tán dọc – % thay đổi theo từng mã, nhóm theo ngành ====
                st.subheader("🎯 Biểu đồ phân tán – Thay đổi giá theo mã cổ phiếu, nhóm theo ngành")

                # Lọc các dòng không có giá trị thay đổi
                df_valid = df_filtered[df_filtered['Change'].notnull() & df_filtered['Industry'].notnull()]

                # Tạo biểu đồ scatter dạng strip plot
                fig_strip = px.scatter(
                    df_valid,
                    x="Ticker",          # Trục X là mã cổ phiếu
                    y="Change",          # Trục Y là % thay đổi giá
                    size="Volume",       # Kích thước điểm theo khối lượng
                    color="Industry",    # Tô màu theo ngành
                    hover_name="Ticker", # Hover hiển thị mã cổ phiếu
                    hover_data={
                        "Change": True,
                        "Volume": True,
                        "Industry": True
                    },
                    title="Mức thay đổi giá các cổ phiếu theo ngành (kích thước = khối lượng giao dịch)",
                )

                # Cập nhật hovertemplate để định dạng volume với dấu phân cách hàng nghìn
                fig_strip.update_traces(
                    hovertemplate="<b>%{hovertext}</b><br>%{x}: %{y:.2f}%<br>Volume: %{marker.size:,.0f}<extra></extra>"
                )

                # Tùy chỉnh giao diện biểu đồ
                fig_strip.update_traces(marker=dict(opacity=0.7, line=dict(width=0.5, color='DarkSlateGrey')))
                fig_strip.update_layout(
                    template="plotly_white",
                    xaxis_title="Mã cổ phiếu",
                    yaxis_title="% Thay đổi giá",
                    height=600
                )

                # Hiển thị biểu đồ
                st.plotly_chart(fig_strip, use_container_width=True)                

                # ==== Biểu đồ 6: Boxplot phân bố % thay đổi theo mã cổ phiếu ====
                st.subheader("📦 Phân bố % thay đổi theo từng mã cổ phiếu")

                # Loại bỏ giá trị NaN
                df_box = df_filtered.dropna(subset=["Ticker", "Change"])

                # Vẽ biểu đồ boxplot
                fig_box = px.box(
                    df_box,
                    x="Ticker",
                    y="Change",
                    points="all",  # Hiển thị toàn bộ điểm
                    color="Ticker",
                    title="Phân bố % thay đổi theo từng mã cổ phiếu",
                    labels={"Change": "% Thay đổi", "Ticker": "Mã cổ phiếu"}
                )

                # Định dạng hover với 2 chữ số thập phân
                fig_box.update_traces(
                    hovertemplate="<b>Mã cổ phiếu: %{x}</b><br>% Thay đổi: %{y:.2f}%<extra></extra>",
                    marker=dict(opacity=0.5, size=6)
                )

                # Tùy chỉnh giao diện biểu đồ
                fig_box.update_layout(
                    template="plotly_white",
                    height=700,
                    xaxis_title="Mã cổ phiếu",
                    yaxis_title="% Thay đổi",
                    showlegend=False,
                    font=dict(size=14),
                    margin=dict(t=60, b=60, l=40, r=40)
                )

                # Hiển thị biểu đồ
                st.plotly_chart(fig_box, use_container_width=True)

                
            else:  # Nếu chọn phân tích Thị Trường
                # ==== Phân tích Thị Trường ====
                
                # Tính toán theo từng ngành (Industry)
                df_market = df.groupby('Industry').agg({
                    'close': 'mean', 
                    'Change': 'mean', 
                    'Volume': 'sum'
                }).reset_index()
                
                # ==== Biểu đồ 1: Biểu đồ tổng quan thị trường theo ngành ====
                # ==== Tính toán dữ liệu bổ sung ====
                # Phân loại tăng/giảm/không đổi
                df['change_category'] = pd.cut(
                    df['Change'],
                    bins=[-float('inf'), -0.01, 0.01, float('inf')],
                    labels=['Giảm', 'Không đổi', 'Tăng']
                )

                # Đếm số lượng mã tăng/giảm/không đổi theo ngành
                industry_counts = df.groupby(['Industry', 'change_category']).size().unstack(fill_value=0).reset_index()

                # Kết hợp với tổng khối lượng (đã tính sẵn trong df_market)
                df_combined = pd.merge(df_market, industry_counts, on='Industry')

                # Tạo cột nhãn hiển thị chi tiết
                df_combined['custom_label'] = df_combined.apply(
                    lambda row: f"{row['Industry']}<br>Tổng mã: {row['Tăng'] + row['Giảm'] + row['Không đổi']}<br>"
                                f"Tăng: {row['Tăng']} | Giảm: {row['Giảm']} | Không đổi: {row['Không đổi']}", axis=1
                )

                # Biểu đồ Hình Tròn
                fig_market = px.pie(
                    df_combined,
                    names='Industry',
                    values='Volume',
                    title="Tỷ trọng khối lượng giao dịch theo ngành",
                    hole=0.4,
                    color_discrete_sequence=px.colors.qualitative.Set3
                )

                # Gán customdata thủ công và chỉnh hovertemplate
                fig_market.update_traces(
                    customdata=df_combined[['custom_label']].values,  # Truyền customdata đúng cách, chỉ lấy custom_label
                    hovertemplate=(
                        "<b>%{label}</b><br>" +  # Hiển thị tên ngành
                        "%{customdata[0]}<br>" +  # Hiển thị chi tiết từ customdata[0]
                        "Khối lượng: %{value:,}<br>" +  # Hiển thị khối lượng
                        "<extra></extra>"  # Bỏ phần thông tin thêm (mặc định)
                    ),
                    textinfo='label',  # Hiển thị chỉ tên ngành trên nhãn
                    textposition='inside'  # Đặt nhãn bên trong hình tròn
                )

                # Thay đổi layout để biểu đồ lớn hơn
                fig_market.update_layout(
                    title="Tỷ trọng khối lượng giao dịch theo ngành",
                    margin=dict(t=50, l=50, r=50, b=50),  # Điều chỉnh lề để mở rộng không gian
                    width=800,  # Chiều rộng của biểu đồ
                    height=600  # Chiều cao của biểu đồ
                )

                st.plotly_chart(fig_market, use_container_width=True)

                # ==== Biểu đồ 2: Biểu đồ thay đổi giá trung bình theo ngành ====
                st.subheader("📈 Biểu đồ thay đổi giá trung bình theo ngành")

                # Tạo biểu đồ cột
                fig_change = px.bar(
                    df_market,
                    x="Industry",
                    y="Change",
                    color="Industry",
                    title="Thay đổi giá trung bình theo ngành",
                    labels={"Change": "% thay đổi giá"}
                )

                # Cập nhật hovertemplate để hiển thị 2 chữ số thập phân
                fig_change.update_traces(
                    hovertemplate="<b>%{x}</b><br>% thay đổi: %{y:.2f}%<extra></extra>"
                )

                # Hiển thị biểu đồ
                st.plotly_chart(fig_change, use_container_width=True)
                
                # ==== Tạo biểu đồ tương quan về số mã tăng, giảm, không đổi giữa các ngành của thị trường ====

                # Tính toán số lượng mã tăng, giảm, không đổi trong từng ngành
                df['change_category'] = pd.cut(df['Change'], 
                                               bins=[-float('inf'), -0.01, 0.01, float('inf')], 
                                               labels=['Giảm', 'Không đổi', 'Tăng'])

                # Tính số lượng mã cho từng loại thay đổi (Tăng, Giảm, Không đổi) trong từng ngành
                industry_change_count = df.groupby(['Industry', 'change_category']).size().unstack(fill_value=0)

                # Hiển thị biểu đồ Stacked Bar: Tương quan số mã Tăng, Giảm, Không đổi giữa các ngành
                st.subheader("📊 Tương quan số mã tăng, giảm, không đổi giữa các ngành")

                # Tạo biểu đồ Stacked Bar với Plotly
                fig_industry_change = px.bar(
                    industry_change_count,
                    x=industry_change_count.index,  # Nhóm ngành
                    y=industry_change_count.columns,  # Các loại thay đổi (Tăng, Giảm, Không đổi)
                    title="Tương quan số mã Tăng, Giảm, Không đổi giữa các Ngành của Thị Trường",
                    labels={"value": "Số lượng mã cổ phiếu", "Industry": "Nhóm Ngành"},
                    color_discrete_map={"Giảm": "#E74C3C", "Không đổi": "#F1C40F", "Tăng": "#2ECC71"},
                    barmode="stack"  # Chế độ biểu đồ chồng (Stacked)
                )

                # Hiển thị biểu đồ Plotly trong Streamlit
                st.plotly_chart(fig_industry_change, use_container_width=True)
                
                # ==== Biểu đồ 4: Biểu đồ phân tán dọc – % thay đổi theo từng mã, nhóm theo ngành ====
                st.subheader("🎯 Biểu đồ phân tán – Thay đổi giá theo nhóm ngành")

                # Lọc các dòng không có giá trị thay đổi
                df_valid = df[df['Change'].notnull() & df['Industry'].notnull()]

                # Tạo biểu đồ scatter dạng strip plot
                fig_strip = px.scatter(
                    df_valid,
                    x="Industry",          # Trục X là nhóm ngành
                    y="Change",            # Trục Y là % thay đổi giá
                    size="Volume",         # Kích thước điểm theo khối lượng
                    color="Industry",      # Tô màu theo ngành
                    hover_name="Ticker",   # Hover hiển thị mã cổ phiếu
                    hover_data={
                        "Change": True,
                        "Volume": True,
                        "Industry": True
                    },
                    title="Mức thay đổi giá các cổ phiếu theo ngành (kích thước = khối lượng giao dịch)",
                )
                
                # Cập nhật hovertemplate để định dạng volume với dấu phân cách hàng nghìn
                fig_strip.update_traces(
                    hovertemplate="<b>%{hovertext}</b><br>%{x}: %{y:.2f}%<br>Volume: %{marker.size:,.0f}<extra></extra>"
                )

                # Tùy chỉnh giao diện biểu đồ
                fig_strip.update_traces(marker=dict(opacity=0.7, line=dict(width=0.5, color='DarkSlateGrey')))
                fig_strip.update_layout(
                    template="plotly_white",
                    xaxis_title="Nhóm ngành",
                    yaxis_title="% Thay đổi giá",
                    height=600
                )

                # Hiển thị biểu đồ
                st.plotly_chart(fig_strip, use_container_width=True)
                
                # ==== Biểu đồ 5: Độ lệch chuẩn của % thay đổi theo từng ngành (Line Chart) ====
                st.subheader("📈 Độ lệch chuẩn % thay đổi theo từng ngành (Line Chart)")

                # Tính toán độ lệch chuẩn cho từng ngành
                industry_std = df.groupby("Industry")["Change"].std().reset_index()
                industry_std.columns = ["Industry", "Std_Change"]
                industry_std = industry_std.dropna().sort_values("Std_Change", ascending=False)

                # Vẽ biểu đồ đường
                fig_line = px.line(
                    industry_std,
                    x="Industry",
                    y="Std_Change",
                    markers=True,
                    title="📈 Độ lệch chuẩn % thay đổi theo từng ngành",
                    labels={"Industry": "Ngành", "Std_Change": "Độ lệch chuẩn (%)"},
                    color_discrete_sequence=["#2ECC71"]  # Màu xanh ngọc
                )

                # Hiển thị giá trị hover dạng 2 số thập phân
                fig_line.update_traces(
                    line=dict(width=3),
                    marker=dict(size=8, color="#27AE60", line=dict(width=1, color="#1E8449")),
                    hovertemplate="<b>%{x}</b><br>Độ lệch chuẩn: %{y:.2f}%<extra></extra>"
                )

                # Tùy chỉnh giao diện
                fig_line.update_layout(
                    template="plotly_white",
                    xaxis_title="Ngành",
                    yaxis_title="Độ lệch chuẩn (%)",
                    height=500,
                    font=dict(size=14),
                    title_font=dict(size=20, color="#145A32", family="Arial"),
                    margin=dict(t=60, b=60, l=40, r=40)
                )

                # Hiển thị biểu đồ
                st.plotly_chart(fig_line, use_container_width=True)
                
                # ==== Biểu đồ 6: Boxplot phân bố % thay đổi theo ngành ====
                st.subheader("📦 Phân bố % thay đổi theo từng ngành (Boxplot)")

                # Loại bỏ giá trị NaN
                df_box = df.dropna(subset=["Industry", "Change"])

                # Vẽ biểu đồ boxplot
                fig_box = px.box(
                    df_box,
                    x="Industry",
                    y="Change",
                    points="all",  # Hiển thị toàn bộ điểm
                    color="Industry",
                    title="Phân bố % thay đổi theo từng ngành",
                    labels={"Change": "% Thay đổi", "Industry": "Ngành"}
                )
                
                # Định dạng hover với 2 chữ số thập phân
                fig_box.update_traces(
                    hovertemplate="<b>Ngành: %{x}</b><br>% Thay đổi: %{y:.2f}%<extra></extra>",
                    marker=dict(opacity=0.5, size=6)
                )

                # Tùy chỉnh giao diện biểu đồ
                fig_box.update_layout(
                    template="plotly_white",
                    height=700,
                    xaxis_title="Ngành",
                    yaxis_title="% Thay đổi",
                    showlegend=False,
                    font=dict(size=14),
                    margin=dict(t=60, b=60, l=40, r=40)
                )

                st.plotly_chart(fig_box, use_container_width=True)
                
                # ==== Biểu đồ 7: Trung bình và Độ lệch chuẩn theo ngành ====
                st.subheader("📊 Trung bình và Độ lệch chuẩn % thay đổi theo từng ngành")

                # Tính toán thống kê
                industry_stats = df.groupby("Industry")["Change"].agg(["mean", "std"]).reset_index()
                industry_stats = industry_stats.dropna().sort_values("mean", ascending=False)
                industry_stats = industry_stats.rename(columns={"mean": "Mean_Change", "std": "Std_Change"})

                # Biểu đồ combo cột
                fig_combo = go.Figure()

                # Cột Trung bình
                fig_combo.add_trace(go.Bar(
                    x=industry_stats["Industry"],
                    y=industry_stats["Mean_Change"],
                    name="Trung bình (%)",
                    marker_color='#2ECC71',
                    hovertemplate="<b>%{x}</b><br>Trung bình: %{y:.2f}%<extra></extra>"
                ))

                # Cột Độ lệch chuẩn
                fig_combo.add_trace(go.Bar(
                    x=industry_stats["Industry"],
                    y=industry_stats["Std_Change"],
                    name="Độ lệch chuẩn (%)",
                    marker_color='#F5B041',
                    hovertemplate="<b>%{x}</b><br>Độ lệch chuẩn: %{y:.2f}%<extra></extra>"
                ))

                # Layout tùy chỉnh
                fig_combo.update_layout(
                    title="📊 Trung bình và Độ lệch chuẩn % thay đổi theo từng ngành",
                    barmode='group',
                    xaxis_title="Ngành",
                    yaxis_title="Giá trị (%)",
                    height=600,
                    template="plotly_white",
                    font=dict(size=14),
                    margin=dict(t=60, b=60, l=40, r=40)
                )

                # Hiển thị biểu đồ
                st.plotly_chart(fig_combo, use_container_width=True)         
                
                
with tab8:
    st.title("📝 Phân tích tài chính doanh nghiệp")

    st.markdown("Chọn nhóm ngành để phân tích dữ liệu biến động của ngành.")
    # Dropdown cho tab5 và tab9
    selected_dropdown = st.selectbox("Chọn chức năng", ["Lấy dữ liệu", "Phân tích tài chính doanh nghiệp"])

    if selected_dropdown == "Lấy dữ liệu":
    # ==== TAB 5 ====
        with st.expander("Lấy dữ liệu", expanded=True):
            st.title("📋 Lấy dữ liệu")

            st.markdown("""
            Nhập mã cổ phiếu để xem các chỉ số tài chính như ROE, ROA, EPS, Nợ/Vốn chủ sở hữu, v.v.  
            Nguồn dữ liệu: VCI (vnstock)
            """)

            symbol = st.text_input("Nhập mã cổ phiếu:", value="VNM", key="symbol_tab4").strip().upper()
            period = st.selectbox("Chọn chu kỳ:", ["year", "quarter"], index=0)
            lang = st.radio("Ngôn ngữ hiển thị:", ["vi", "en"], horizontal=True)
            
            def format_number(x):
                """Định dạng số với dấu chấm phân cách hàng nghìn"""
                if isinstance(x, (int, float)):
                    return f"{x:,.0f}".replace(",", ".")  # Định dạng số và thay dấu phẩy bằng dấu chấm
                return x

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


    if selected_dropdown == "Phân tích tài chính doanh nghiệp":
    # ==== TAB 9 ====
        with st.expander("Phân tích tài chính doanh nghiệp", expanded=True):
            st.title("Phân tích tài chính doanh nghiệp")

            def clean_column(col):
                col = col.strip()
                col = re.sub(r'\s+', '_', col)
                col = re.sub(r'[^\w/]', '', col)  # Loại bỏ ký tự đặc biệt, trừ dấu "/"
                return col
              
            # Hàm đọc và chuẩn hóa dữ liệu cho chỉ số tài chính
            def load_data(file, num_periods=8):
                df = pd.read_csv(file)
                df.columns = [clean_column(col) for col in df.columns]

                # Tạo cột 'Kỳ_hiển_thị'
                def format_period(row):
                    if int(row['Kỳ']) == 5:
                        return f"Năm {int(row['Năm'])}"
                    else:
                        return f"Q{int(row['Kỳ'])}/{int(row['Năm'])}"

                df["Kỳ_hiển_thị"] = df.apply(format_period, axis=1)

                # Lấy 8 kỳ gần nhất
                df = df.sort_values(by=["Năm", "Kỳ"], ascending=[False, False]).head(num_periods)

                # Sau đó sắp xếp lại tăng dần để biểu đồ đúng thứ tự thời gian
                df = df.sort_values(by=["Năm", "Kỳ"], ascending=[True, True]).reset_index(drop=True)

                return df

            # Hàm vẽ biểu đồ bằng Plotly (giữ nguyên theo yêu cầu)
            def plot_data(df, x_col, y_cols, plot_type, title):
                # Lấy tên cổ phiếu từ cột 'CP' (tên cổ phiếu trong dữ liệu)
                stock_name = df['CP'].iloc[0]  # Giả sử tất cả các dòng có cùng tên cổ phiếu

                # Cập nhật tiêu đề để bao gồm tên cổ phiếu
                title = f"{stock_name} - {title}"

                fig = None
                if plot_type == "Line":
                    fig = px.line(df, x=x_col, y=y_cols, markers=True, title=title)
                elif plot_type == "Bar":
                    fig = px.bar(df, x=x_col, y=y_cols, barmode='group', title=title)
                elif plot_type == "Area":
                    fig = px.area(df, x=x_col, y=y_cols, title=title)

                if fig:
                    fig.update_layout(xaxis_title=x_col, yaxis_title="Giá trị")
                    st.plotly_chart(fig)
            # Lựa chọn số kỳ ngay trong tab
            num_periods = st.slider("Chọn số kỳ gần nhất để hiển thị", min_value=4, max_value=20, value=8)        

            # Tải lên file CSV cho chỉ số tài chính
            financial_file = st.file_uploader("Tải lên file CSV cho chỉ số tài chính", type=["csv"])
            if financial_file is not None:
                try:
                    df = load_data(financial_file, num_periods)
                    st.subheader("Dữ liệu chỉ số tài chính kỳ")
                    st.dataframe(df)

                    # Các nhóm chỉ số (sau khi chuẩn hóa)
                    financial_ratios = ['Nợ/VCSH', 'ROE_', 'ROA_', 'ROIC_', 'Biên_EBIT_', 'Biên_lợi_nhuận_gộp_', 'Biên_lợi_nhuận_ròng_', 
                                        'Chỉ_số_thanh_toán_hiện_thời', 'Chỉ_số_thanh_toán_nhanh']
                    efficiency_metrics = ['Vòng_quay_tài_sản', 'Vòng_quay_TSCĐ', 'Số_ngày_thu_tiền_bình_quân', 
                                          'Số_ngày_tồn_kho_bình_quân', 'Vòng_quay_hàng_tồn_kho']
                    valuation_metrics = ['P/E', 'P/B', 'P/S', 'EV/EBITDA', 'EPS_VND', 'BVPS_VND']

                    metric_group = st.sidebar.selectbox("Nhóm chỉ số", 
                                                        ['Chỉ số tài chính', 'Hiệu quả hoạt động', 'Định giá'])

                    if metric_group == 'Chỉ số tài chính':
                        selected_metrics = st.sidebar.multiselect("Chọn chỉ số", financial_ratios, default=financial_ratios[:3])
                    elif metric_group == 'Hiệu quả hoạt động':
                        selected_metrics = st.sidebar.multiselect("Chọn chỉ số", efficiency_metrics, default=efficiency_metrics[:3])
                    else:
                        selected_metrics = st.sidebar.multiselect("Chọn chỉ số", valuation_metrics, default=valuation_metrics[:3])

                    plot_type = st.sidebar.selectbox("Loại biểu đồ", ['Line', 'Bar', 'Area'])

                    # Vẽ biểu đồ
                    if selected_metrics:
                        available_cols = df.columns.tolist()
                        valid_metrics = [col for col in selected_metrics if col in available_cols]

                        if valid_metrics:
                            plot_data(df, "Kỳ_hiển_thị", valid_metrics, plot_type,
                                      f"Biểu đồ {plot_type} cho các chỉ số đã chọn")
                        else:
                            st.warning("Không có chỉ số hợp lệ trong dữ liệu.")

                        # Cho phép tải xuống dữ liệu đã chọn
                        if st.button("Xuất dữ liệu đã chọn"):
                            output = df[["Kỳ_hiển_thị"] + selected_metrics]
                            st.download_button(
                                label="Tải xuống CSV",
                                data=output.to_csv(index=False).encode('utf-8'),
                                file_name='selected_financial_data.csv',
                                mime='text/csv',
                            )

                except Exception as e:
                    st.error(f"Có lỗi xảy ra: {str(e)}")
            else:
                st.info("Vui lòng tải lên file CSV cho chỉ số tài chính để bắt đầu phân tích")

            # Tải lên file CSV cho bảng cân đối kế toán
            balance_sheet_file = st.file_uploader("Tải lên file CSV cho bảng cân đối kế toán", type=["csv"])
            if balance_sheet_file is not None:
                try:
                    df_balance_sheet = load_data(balance_sheet_file, num_periods)
                    st.subheader("Dữ liệu bảng cân đối kế toán")
                    st.dataframe(df_balance_sheet)

                    # Các nhóm chỉ số bảng cân đối kế toán
                    balance_sheet_metrics = {
                        'Tài sản': [
                            'TÀI_SẢN_NGẮN_HẠN_đồng', 'Tiền_và_tương_đương_tiền_đồng', 'Giá_trị_thuần_đầu_tư_ngắn_hạn_đồng', 
                            'Các_khoản_phải_thu_ngắn_hạn_đồng', 'Hàng_tồn_kho_ròng', 'Tài_sản_lưu_động_khác', 
                            'TÀI_SẢN_DÀI_HẠN_đồng', 'Phải_thu_về_cho_vay_dài_hạn_đồng', 'Tài_sản_cố_định_đồng', 
                            'Giá_trị_ròng_tài_sản_đầu_tư', 'Đầu_tư_dài_hạn_đồng', 'Lợi_thế_thương_mại', 'Tài_sản_dài_hạn_khác'
                        ],
                        'Nợ phải trả': [
                            'NỢ_PHẢI_TRẢ_đồng', 'Nợ_ngắn_hạn_đồng', 'Nợ_dài_hạn_đồng', 'Trả_trước_cho_người_bán_ngắn_hạn_đồng', 
                            'Phải_thu_về_cho_vay_ngắn_hạn_đồng', 'Vay_và_nợ_thuê_tài_chính_dài_hạn_đồng', 
                            'Người_mua_trả_tiền_trước_ngắn_hạn_đồng', 'Vay_và_nợ_thuê_tài_chính_ngắn_hạn_đồng'
                        ],
                        'Vốn chủ sở hữu': [
                            'VỐN_CHỦ_SỞ_HỮU_đồng', 'Vốn_và_các_quỹ_đồng', 'Các_quỹ_khác', 'Lãi_chưa_phân_phối_đồng', 
                            'LỢI_ÍCH_CỦA_CỔ_ĐÔNG_THIỂU_SỐ', 'TỔNG_CỘNG_NGUỒN_VỐN_đồng', 'Quỹ_đầu_tư_và_phát_triển_đồng', 
                            'Cổ_phiếu_phổ_thông_đồng', 'Vốn_góp_của_chủ_sở_hữu_đồng', 'Lợi_thế_thương_mại_đồng', 
                            'Trả_trước_dài_hạn_đồng', 'Tài_sản_dài_hạn_khác_đồng', 'Phải_thu_dài_hạn_khác_đồng', 
                            'Phải_thu_dài_hạn_đồng'
                        ]
                    }

                    metric_group_balance_sheet = st.sidebar.selectbox("Nhóm chỉ số bảng cân đối kế toán", 
                                                                      ['Tài sản', 'Nợ phải trả', 'Vốn chủ sở hữu'])

                    if metric_group_balance_sheet == 'Tài sản':
                        selected_metrics_balance_sheet = st.sidebar.multiselect("Chọn chỉ số", balance_sheet_metrics['Tài sản'], default=balance_sheet_metrics['Tài sản'][:3])
                    elif metric_group_balance_sheet == 'Nợ phải trả':
                        selected_metrics_balance_sheet = st.sidebar.multiselect("Chọn chỉ số", balance_sheet_metrics['Nợ phải trả'], default=balance_sheet_metrics['Nợ phải trả'][:3])
                    else:
                        selected_metrics_balance_sheet = st.sidebar.multiselect("Chọn chỉ số", balance_sheet_metrics['Vốn chủ sở hữu'], default=balance_sheet_metrics['Vốn chủ sở hữu'][:3])

                    # Thực hiện các bước xử lý và vẽ biểu đồ như trước

                    plot_type_balance_sheet = st.sidebar.selectbox("Loại biểu đồ bảng cân đối kế toán", ['Line', 'Bar', 'Area'])

                    # Vẽ biểu đồ bảng cân đối kế toán
                    if selected_metrics_balance_sheet:
                        available_cols_balance_sheet = df_balance_sheet.columns.tolist()
                        valid_metrics_balance_sheet = [col for col in selected_metrics_balance_sheet if col in available_cols_balance_sheet]

                        if valid_metrics_balance_sheet:
                            plot_data(df_balance_sheet, "Kỳ_hiển_thị", valid_metrics_balance_sheet, plot_type_balance_sheet,
                                                    f"Biểu đồ {plot_type_balance_sheet} cho các chỉ số bảng cân đối kế toán đã chọn")
                        else:
                            st.warning("Không có chỉ số hợp lệ trong dữ liệu.")

                        # Cho phép tải xuống dữ liệu bảng cân đối kế toán đã chọn
                        if st.button("Xuất dữ liệu bảng cân đối kế toán đã chọn"):
                            output_balance_sheet = df_balance_sheet[["Kỳ_hiển_thị"] + selected_metrics_balance_sheet]
                            st.download_button(
                                label="Tải xuống CSV",
                                data=output_balance_sheet.to_csv(index=False).encode('utf-8'),
                                file_name='selected_balance_sheet_data.csv',
                                mime='text/csv',
                            )

                except Exception as e:
                    st.error(f"Có lỗi xảy ra khi tải bảng cân đối kế toán: {str(e)}")
            else:
                st.info("Vui lòng tải lên file CSV cho bảng cân đối kế toán để bắt đầu phân tích")

            # Tải lên file CSV cho báo cáo kết quả kinh doanh
            income_statement_file = st.file_uploader("Tải lên file CSV cho báo cáo kết quả kinh doanh", type=["csv"])
            if income_statement_file is not None:
                try:
                    df_income_statement = load_data(income_statement_file, num_periods)
                    st.subheader("Dữ liệu báo cáo kết quả kinh doanh")
                    st.dataframe(df_income_statement)

                    # Các nhóm chỉ số báo cáo kết quả kinh doanh
                    income_statement_metrics = {
                        'Doanh thu và lợi nhuận': [
                            'Doanh_thu_đồng', 'Doanh_thu_bán_hàng_và_cung_cấp_dịch_vụ', 'Các_khoản_giảm_trừ_doanh_thu',
                            'Doanh_thu_thuần', 'Giá_vốn_hàng_bán', 'Lãi_gộp', 'Lãi_Lỗ_từ_hoạt_động_kinh_doanh',
                            'Lợi_nhuận_thuần', 'LN_trước_thuế', 'Lợi_nhuận_sau_thuế_của_Cổ_đông_công_ty_mẹ_đồng',
                            'Cổ_đông_thiểu_số', 'Cổ_đông_của_Công_ty_mẹ'
                        ],
                        'Chi phí và tài chính': [
                            'Chi_phí_tài_chính', 'Chi_phí_tiền_lãi_vay', 'Chi_phí_bán_hàng', 'Chi_phí_quản_lý_DN',
                            'Chi_phí_thuế_TNDN_hiện_hành', 'Chi_phí_thuế_TNDN_hoãn_lại',
                            'Thu_nhập_tài_chính', 'Thu_nhập_khác', 'Thu_nhập/Chi_phí_khác'
                        ],
                        'Lợi nhuận và tăng trưởng': [
                            'Tăng_trưởng_doanh_thu_', 'Tăng_trưởng_lợi_nhuận_',
                            'Lợi_nhuận_khác', 'Lãi/lỗ_từ_công_ty_liên_doanh', 'Lãi_lỗ_trong_công_ty_liên_doanh_liên_kết'
                        ]
                    }

                    # Chọn nhóm chỉ số
                    metric_group_income = st.sidebar.selectbox("Nhóm chỉ số báo cáo KQKD", list(income_statement_metrics.keys()))

                    # Hiển thị multiselect chỉ số
                    selected_metrics_income = st.sidebar.multiselect(
                        "Chọn chỉ số",
                        income_statement_metrics[metric_group_income],
                        default=income_statement_metrics[metric_group_income][:3]
                    )

                    # Loại biểu đồ
                    plot_type_income = st.sidebar.selectbox("Loại biểu đồ báo cáo KQKD", ['Line', 'Bar', 'Area'])

                    # Vẽ biểu đồ
                    if selected_metrics_income:
                        available_cols_income = df_income_statement.columns.tolist()
                        valid_metrics_income = [col for col in selected_metrics_income if col in available_cols_income]

                        if valid_metrics_income:
                            plot_data(
                                df_income_statement,
                                "Kỳ_hiển_thị",  # Cột thể hiện thời gian — hãy chắc chắn file của bạn có cột này
                                valid_metrics_income,
                                plot_type_income,
                                f"Biểu đồ {plot_type_income} cho các chỉ số KQKD đã chọn"
                            )
                        else:
                            st.warning("Không có chỉ số hợp lệ trong dữ liệu.")

                        # Cho phép tải xuống dữ liệu
                        if st.button("Xuất dữ liệu báo cáo KQKD đã chọn"):
                            output_income = df_income_statement[["Kỳ_hiển_thị"] + valid_metrics_income]
                            st.download_button(
                                label="Tải xuống CSV",
                                data=output_income.to_csv(index=False).encode('utf-8'),
                                file_name='selected_income_statement_data.csv',
                                mime='text/csv',
                            )

                except Exception as e:
                    st.error(f"Có lỗi xảy ra khi tải báo cáo kết quả kinh doanh: {str(e)}")
            else:
                st.info("Vui lòng tải lên file CSV cho báo cáo kết quả kinh doanh để bắt đầu phân tích")
          
            # Tải lên file CSV cho báo cáo lưu chuyển tiền tệ
            cash_flow_file = st.file_uploader("Tải lên file CSV cho báo cáo lưu chuyển tiền tệ", type=["csv"])
            if cash_flow_file is not None:
                try:
                    df_cash_flow = load_data(cash_flow_file, num_periods)
                    st.subheader("Dữ liệu báo cáo lưu chuyển tiền tệ")
                    st.dataframe(df_cash_flow)

                    # Các nhóm chỉ số báo cáo lưu chuyển tiền tệ
                    cash_flow_metrics = {
                        'Hoạt động kinh doanh': [
                            'Lãi/Lỗ_ròng_trước_thuế', 'Khấu_hao_TSCĐ', 'Dự_phòng_RR_tín_dụng',
                            'Lãi/Lỗ_chênh_lệch_tỷ_giá_chưa_thực_hiện', 'Lãi/Lỗ_từ_thanh_lý_tài_sản_cố_định',
                            'Lãi/Lỗ_từ_hoạt_động_đầu_tư', 'Thu_nhập_lãi', 'Thu_lãi_và_cổ_tức',
                            'Lưu_chuyển_tiền_thuần_từ_HĐKD_trước_thay_đổi_VLĐ',
                            'Tăng/Giảm_các_khoản_phải_thu', 'Tăng/Giảm_hàng_tồn_kho',
                            'Tăng/Giảm_các_khoản_phải_trả', 'Tăng/Giảm_chi_phí_trả_trước',
                            'Chi_phí_lãi_vay_đã_trả', 'Tiền_thu_nhập_doanh_nghiệp_đã_trả',
                            'Tiền_thu_khác_từ_các_hoạt_động_kinh_doanh', 'Tiền_chi_khác_từ_các_hoạt_động_kinh_doanh',
                            'Lưu_chuyển_tiền_tệ_ròng_từ_các_hoạt_động_SXKD'
                        ],
                        'Hoạt động đầu tư': [
                            'Mua_sắm_TSCĐ', 'Tiền_thu_được_từ_thanh_lý_tài_sản_cố_định',
                            'Tiền_chi_cho_vay_mua_công_cụ_nợ_của_đơn_vị_khác_đồng',
                            'Tiền_thu_hồi_cho_vay_bán_lại_các_công_cụ_nợ_của_đơn_vị_khác_đồng',
                            'Đầu_tư_vào_các_doanh_nghiệp_khác', 'Tiền_thu_từ_việc_bán_các_khoản_đầu_tư_vào_doanh_nghiệp_khác',
                            'Tiền_thu_cổ_tức_và_lợi_nhuận_được_chia',
                            'Lưu_chuyển_từ_hoạt_động_đầu_tư'
                        ],
                        'Hoạt động tài chính': [
                            'Tăng_vốn_cổ_phần_từ_góp_vốn_và_hoặc_phát_hành_cổ_phiếu',
                            'Chi_trả_cho_việc_mua_lại_trả_cổ_phiếu', 'Tiền_thu_được_các_khoản_đi_vay',
                            'Tiền_trả_các_khoản_đi_vay', 'Cổ_tức_đã_trả',
                            'Lưu_chuyển_tiền_từ_hoạt_động_tài_chính'
                        ],
                        'Dòng tiền cuối kỳ': [
                            'Lưu_chuyển_tiền_thuần_trong_kỳ', 'Tiền_và_tương_đương_tiền',
                            'Ảnh_hưởng_của_chênh_lệch_tỷ_giá', 'Tiền_và_tương_đương_tiền_cuối_kỳ'
                        ]
                    }

                    # Chọn nhóm chỉ số
                    metric_group_cash_flow = st.sidebar.selectbox("Nhóm chỉ số lưu chuyển tiền tệ", list(cash_flow_metrics.keys()))

                    # Hiển thị multiselect chỉ số
                    selected_metrics_cash_flow = st.sidebar.multiselect(
                        "Chọn chỉ số",
                        cash_flow_metrics[metric_group_cash_flow],
                        default=cash_flow_metrics[metric_group_cash_flow][:3]
                    )

                    # Loại biểu đồ
                    plot_type_cash_flow = st.sidebar.selectbox("Loại biểu đồ lưu chuyển tiền tệ", ['Line', 'Bar', 'Area'])

                    # Vẽ biểu đồ
                    if selected_metrics_cash_flow:
                        available_cols_cash = df_cash_flow.columns.tolist()
                        valid_metrics_cash = [col for col in selected_metrics_cash_flow if col in available_cols_cash]

                        if valid_metrics_cash:
                            plot_data(
                                df_cash_flow,
                                "Kỳ_hiển_thị",  # Đảm bảo file có cột này
                                valid_metrics_cash,
                                plot_type_cash_flow,
                                f"Biểu đồ {plot_type_cash_flow} cho các chỉ số lưu chuyển tiền tệ đã chọn"
                            )
                        else:
                            st.warning("Không có chỉ số hợp lệ trong dữ liệu.")

                        # Cho phép tải xuống dữ liệu
                        if st.button("Xuất dữ liệu báo cáo lưu chuyển tiền tệ đã chọn"):
                            output_cash = df_cash_flow[["Kỳ_hiển_thị"] + valid_metrics_cash]
                            st.download_button(
                                label="Tải xuống CSV",
                                data=output_cash.to_csv(index=False).encode('utf-8'),
                                file_name='selected_cash_flow_data.csv',
                                mime='text/csv',
                            )

                except Exception as e:
                    st.error(f"Có lỗi xảy ra khi tải báo cáo lưu chuyển tiền tệ: {str(e)}")
            else:
                st.info("Vui lòng tải lên file CSV cho báo cáo lưu chuyển tiền tệ để bắt đầu phân tích")
            
            
