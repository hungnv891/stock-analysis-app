# app.py

import streamlit as st
from analyzer import analyze_stock, export_to_excel
import os
from datetime import date

st.set_page_config(page_title="Phân Tích Cổ Phiếu", layout="wide")
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
            
            # Tạo 2 cột để hiển thị dữ liệu cân đối
            col1, col2 = st.columns(2)
            
            with col1:
                st.metric("Tổng dòng tiền vào (VND)", summary['Tổng dòng tiền vào (VND)'])
                st.metric("Tổng dòng tiền ra (VND)", summary['Tổng dòng tiền ra (VND)'])
                st.metric("Dòng tiền ròng (VND)", summary['Dòng tiền ròng (VND)'])
                st.metric("Tổng số lệnh mua", summary['Tổng số lệnh mua'])
                st.metric("Tổng số lệnh bán", summary['Tổng số lệnh bán'])
                st.metric("Tỷ lệ mua/bán", f"{summary['Tỷ lệ khối lượng trung bình mua/bán']:,.2f}")
                
            with col2:
                st.metric("Tổng khối lượng", f"{summary['Tổng khối lượng giao dịch']:,.0f}")
                st.metric("Khối lượng TB lệnh mua", f"{summary['Khối lượng trung bình lệnh mua']:,.2f}")
                st.metric("Khối lượng TB lệnh bán", f"{summary['Khối lượng trung bình lệnh bán']:,.2f}")                
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
