# --- Extract Depth Chart & Status Styling ---
depth_order = pdata.get("depth_chart_order")
depth_str = f"{pdata.get('position')}{depth_order}" if depth_order else pdata.get("position")

# In the render loop inside each container:
with p_cols[i % 3]:
    with st.container(border=True):
        col_img, col_info = st.columns([1, 1.4])
        with col_img:
            st.image(p["Headshot"], width=115)
            
            # Status Badge
            if p["Status"] == "Healthy":
                st.caption(f"🟢 **{p['Status']}**")
            elif p["Status"] in ["Questionable", "Doubtful"]:
                st.caption(f"🟡 **{p['Status']}**")
            else:
                st.caption(f"🔴 **{p['Status']}**")

        with col_info:
            st.markdown(f"**{p['Name']}**")
            # Displays Depth Chart Role (e.g., CHI (Week 1) | RB1)
            st.caption(f"{p['Team']} ({p_week_str}) | **{depth_str}**")
            
            m1, m2 = st.columns(2)
            with m1:
                st.metric(
                    label="Proj PPR",
                    value=f"{p['ProjPPR']:.2f}" if p['ProjPPR'] > 0 else "0.00"
                )
            with m2:
                st.metric(
                    label="Avg PPR",
                    value=f"{p['AvgPPR']:.2f}" if p['AvgPPR'] > 0 else "0.00"
                )
