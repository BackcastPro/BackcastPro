import streamlit as st

st.title('タイトルの表示')

btn_1 = st.button('表示')

if btn_1:
    st.text('クリックしました')