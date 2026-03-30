import streamlit as st

# Page config
st.set_page_config(page_title="CampusShare", layout="wide")

# -----------------------
# Mock Data
# -----------------------
items = [
    {"name": "Biology Textbook", "category": "Textbooks", "owner": "James", "days": "3 Days"},
    {"name": "Mini Fridge", "category": "Appliances", "owner": "Sarah", "days": "5 Days"},
    {"name": "Laptop Charger", "category": "Electronics", "owner": "Emily", "days": "1 Day"},
    {"name": "TI-84 Calculator", "category": "School Supplies", "owner": "Alex", "days": "2 Days"},
]

categories = ["Textbooks", "Electronics", "Dorm Essentials", "Sports & Outdoors"]

# -----------------------
# Header
# -----------------------
st.title("🎓 CampusShare")
st.subheader("Borrow & Lend with Fellow Students")

# -----------------------
# Search + Tabs
# -----------------------
col1, col2 = st.columns([3, 1])

with col1:
    search = st.text_input("Search for textbooks, electronics, and more...")

with col2:
    mode = st.radio("", ["Borrow", "Lend"], horizontal=True)

# -----------------------
# Filter Items
# -----------------------
filtered_items = [
    item for item in items
    if search.lower() in item["name"].lower()
]

# -----------------------
# Item Cards
# -----------------------
st.markdown("### Available Items")

cols = st.columns(2)

for i, item in enumerate(filtered_items):
    with cols[i % 2]:
        st.container(border=True)
        st.markdown(f"**{item['name']}**")
        st.caption(item["category"])
        st.write(f"👤 {item['owner']} • ⏱ {item['days']}")
        st.button(f"View {item['name']}", key=item["name"])

# -----------------------
# CTA Button
# -----------------------
st.markdown("---")
st.button("➕ List an Item", use_container_width=True)

# -----------------------
# Categories Section
# -----------------------
st.markdown("## Popular Categories")

cat_cols = st.columns(len(categories))

for i, cat in enumerate(categories):
    with cat_cols[i]:
        st.container(border=True)
        st.markdown(f"### {cat}")