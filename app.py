from inference_sdk import InferenceHTTPClient

import streamlit as st
import sqlite3
from datetime import datetime
import tempfile
import os

st.set_page_config(
    page_title="Smart Shelf Monitoring",
    page_icon="🛒",
    layout="wide"
)

# ---------------- ROBOFLOW ----------------

client = InferenceHTTPClient(
    api_url="https://serverless.roboflow.com",
    api_key="mDTOEVaUTpvRC2APYYMp"
)

# Minimum confidence required
CONFIDENCE_THRESHOLD = 0.50

# ---------------- DATABASE ----------------

conn = sqlite3.connect(
    "inventory.db",
    check_same_thread=False
)

cursor = conn.cursor()

cursor.execute("""
CREATE TABLE IF NOT EXISTS inventory (
    product TEXT PRIMARY KEY,
    stockroom_quantity INTEGER,
    shelf_quantity INTEGER
)
""")

cursor.execute("""
CREATE TABLE IF NOT EXISTS requests (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    product TEXT,
    quantity INTEGER,
    status TEXT,
    time TEXT
)
""")

# Sample supermarket inventory
products = [
    ("Milk", 20, 0),
    ("Biscuits", 15, 2),
    ("Rice", 30, 5),
    ("Soap", 10, 0)
]

for product in products:
    cursor.execute(
        "INSERT OR IGNORE INTO inventory VALUES (?, ?, ?)",
        product
    )

conn.commit()

# ---------------- APP ----------------

st.title("🛒 Smart Shelf Monitoring System")

st.write(
    "Check product availability in the supermarket stockroom."
)

st.header("👤 Customer")

# Upload shelf photo
uploaded_file = st.file_uploader(
    "📷 Take or upload a shelf photo",
    type=["jpg", "jpeg", "png"]
)

if uploaded_file:

    st.image(
        uploaded_file,
        caption="Uploaded Shelf Photo",
        use_container_width=True
    )

    # ---------------- ROBOFLOW AI ----------------

    with tempfile.NamedTemporaryFile(
        delete=False,
        suffix=".jpg"
    ) as temp_file:

        temp_file.write(
            uploaded_file.getbuffer()
        )

        image_path = temp_file.name

    try:

        result = client.run_workflow(
            workspace_name="smithashree20-gmail-com",
            workflow_id="smart-shelf-products",
            images={
                "image": image_path
            },
            use_cache=True
        )

        st.write("AI Detection Result:")
        st.write(result)

    finally:

        os.remove(image_path)

    st.success(
        "Shelf photo uploaded successfully! ✅"
    )

    st.divider()

    # ---------------- AI PRODUCT DETECTION ----------------

    st.subheader("🔍 Product Information")

    predictions = result[0]["predictions"]["predictions"]

    if predictions:

        detected_product = predictions[0]["class"]
        confidence = predictions[0]["confidence"]

        st.write(
            f"🤖 AI detected: **{detected_product}**"
        )

        st.write(
            f"Confidence: **{confidence:.2%}**"
        )

        # Check confidence
        if confidence >= CONFIDENCE_THRESHOLD:

            st.success(
                f"✅ Product identified confidently as **{detected_product}**."
            )

            product = detected_product

            # Get inventory information
            cursor.execute(
                """
                SELECT stockroom_quantity, shelf_quantity
                FROM inventory
                WHERE product = ?
                """,
                (product,)
            )

            inventory_result = cursor.fetchone()

            if inventory_result:

                stockroom_quantity = inventory_result[0]
                shelf_quantity = inventory_result[1]

                # Display information
                col1, col2 = st.columns(2)

                with col1:

                    st.metric(
                        "Shelf Quantity",
                        shelf_quantity
                    )

                with col2:

                    st.metric(
                        "Stockroom Quantity",
                        stockroom_quantity
                    )

                # ---------------- AVAILABILITY ----------------

                if stockroom_quantity > 0:

                    st.success(
                        f"✅ {product} is available in the stockroom."
                    )

                    st.write(
                        f"**{stockroom_quantity} units available.**"
                    )

                    if st.button(
                        "🔔 Notify Staff to Restock"
                    ):

                        cursor.execute(
                            """
                            INSERT INTO requests
                            (product, quantity, status, time)
                            VALUES (?, ?, ?, ?)
                            """,
                            (
                                product,
                                stockroom_quantity,
                                "Pending",
                                datetime.now().strftime(
                                    "%Y-%m-%d %H:%M:%S"
                                )
                            )
                        )

                        conn.commit()

                        st.success(
                            "🔔 Staff has been notified successfully!"
                        )

                else:

                    st.error(
                        f"❌ {product} is not available in the stockroom."
                    )

            else:

                st.warning(
                    f"⚠️ {product} was detected, but it is not in the inventory database."
                )

        else:

            st.warning(
                "⚠️ Product could not be identified confidently."
            )

            st.info(
                "Please upload a clearer shelf image and try again."
            )

    else:

        st.warning(
            "⚠️ No product was detected in the uploaded image."
        )

        st.info(
            "Please upload a clearer shelf image and try again."
        )


# ---------------- STAFF DASHBOARD ----------------

st.divider()

st.header("👷 Staff Dashboard")

st.subheader("🔔 Restocking Requests")

cursor.execute("""
SELECT id, product, quantity, status, time
FROM requests
ORDER BY id DESC
""")

requests = cursor.fetchall()

if requests:

    for request in requests:

        request_id = request[0]
        product_name = request[1]
        quantity = request[2]
        status = request[3]
        request_time = request[4]

        st.write(
            f"### 🛒 {product_name}"
        )

        st.write(
            f"📦 Quantity available in stockroom: **{quantity}**"
        )

        st.write(
            f"🕒 Request time: **{request_time}**"
        )

        st.write(
            f"📌 Status: **{status}**"
        )

        if status == "Pending":

            if st.button(
                "✅ Mark as Restocked",
                key=f"restock_{request_id}"
            ):

                cursor.execute(
                    """
                    UPDATE inventory
                    SET shelf_quantity = shelf_quantity + ?,
                        stockroom_quantity = stockroom_quantity - ?
                    WHERE product = ?
                    """,
                    (
                        quantity,
                        quantity,
                        product_name
                    )
                )

                cursor.execute(
                    """
                    UPDATE requests
                    SET status = 'Completed'
                    WHERE id = ?
                    """,
                    (request_id,)
                )

                conn.commit()

                st.success(
                    f"✅ {product_name} has been restocked successfully!"
                )

                st.rerun()

        st.divider()

else:

    st.info(
        "No restocking requests at the moment."
    )
