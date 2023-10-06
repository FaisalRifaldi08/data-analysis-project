import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
import streamlit as st
from babel.numbers import format_currency
import datetime
import plotly.express as px

sns.set(style='dark')

# Helper function yang dibutuhkan untuk menyiapkan berbagai dataframe

def create_daily_sales_df(df):
    daily_sales_df = df.resample(rule='D', on='order_purchase_timestamp')['payment_value'].sum()
    
    return daily_sales_df

def process_final_df(df):
    filtered_by_status_df = df[df['order_status'].isin(['delivered', 'invoiced'])]
    
    # Hilangkan filter 6 bulan di sini
    product_counts_df = df.groupby(['customer_id', 'product_category_name']).size().reset_index(name='count')
    
    return filtered_by_status_df, product_counts_df

def last_year_payment_data(df):
    last_year = df['order_purchase_timestamp'].max() - pd.DateOffset(years=1)
    last_year_df = df[df['order_purchase_timestamp'] >= last_year]

    payment_counts = last_year_df['payment_type'].value_counts()

    payment_percentages_df = (payment_counts / len(last_year_df)) * 100
    
    return payment_percentages_df

def payment_trends(df):
    last_year = df['order_purchase_timestamp'].max() - pd.DateOffset(years=1)
    last_year_df = df[df['order_purchase_timestamp'] >= last_year]

    payment_trends_df = last_year_df.groupby([last_year_df['order_purchase_timestamp'].dt.strftime('%Y-%m'), 'payment_type']).size().unstack(fill_value=0)
    
    return payment_trends_df

def city_opportunity(df):
    seller_counts = df['seller_city'].value_counts()
    customer_counts = df['customer_city'].value_counts()

    city_opportunity = seller_counts - customer_counts

    city_data = pd.DataFrame({
        'City': city_opportunity.index,
        'Opportunity': city_opportunity.values
    })

    city_opportunity_df = city_data.sort_values(by='Opportunity', ascending=False)
    
    return city_opportunity_df


def delivery_time_and_review(df):
    Q1 = df['delivery_time'].quantile(0.25)
    Q3 = df['delivery_time'].quantile(0.75)
    IQR = Q3 - Q1

    lower_bound = Q1 - 1.5 * IQR
    upper_bound = Q3 + 1.5 * IQR

    df = df[(df['delivery_time'] >= lower_bound) & (df['delivery_time'] <= upper_bound)]

    delivery_time_and_review_df = df.groupby('delivery_time')['review_score'].mean().reset_index()
    
    return delivery_time_and_review_df

def top_3_product_sales(df):
    data = df[['order_purchase_timestamp', 'product_category_name', 'order_item_id']]

    monthly_sales = data.groupby([df['order_purchase_timestamp'].dt.to_period('M'), 'product_category_name'])['order_item_id'].sum().reset_index()

    monthly_sales['order_purchase_timestamp'] = pd.to_datetime(monthly_sales['order_purchase_timestamp'].astype(str))

    top_3_products = monthly_sales.groupby('product_category_name')['order_item_id'].sum().nlargest(3).index

    top_seasonal_products_df = monthly_sales[monthly_sales['product_category_name'].isin(top_3_products)]
    
    return top_seasonal_products_df


# Load cleaned data
Final_df = pd.read_csv("dashboard/Final_df.csv")

# Mengonversi kolom order_purchase_timestamp dan order_delivered_customer_date ke tipe data datetime
datetime_columns = ["order_purchase_timestamp", "order_delivered_customer_date"]
Final_df.sort_values(by="order_purchase_timestamp", inplace=True)
Final_df.reset_index(inplace=True)
for column in datetime_columns:
    Final_df[column] = pd.to_datetime(Final_df[column])

# Sidebar
st.sidebar.image("dashboard/Gambar.png", use_column_width=True)
st.sidebar.title("Dashboard Options")

# Date range selection
min_date = Final_df["order_purchase_timestamp"].min()
max_date = Final_df["order_purchase_timestamp"].max()

start_date, end_date = st.sidebar.date_input("Select Date Range", min_value=min_date, max_value=max_date, value=[min_date, max_date])

start_date = datetime.datetime.combine(start_date, datetime.datetime.min.time())
end_date = datetime.datetime.combine(end_date, datetime.datetime.max.time())

# Filter data
main_df = Final_df[(Final_df["order_purchase_timestamp"] >= start_date) &
                   (Final_df["order_purchase_timestamp"] <= end_date)]



# st.dataframe(main_df)

# Menyiapkan berbagai dataframe
daily_sales_df = create_daily_sales_df(main_df)
filtered_by_status_df, product_counts_df = process_final_df(main_df)
payment_percentages_df = last_year_payment_data(main_df)
payment_trends_df = payment_trends(main_df)
city_opportunity_df = city_opportunity(main_df)
delivery_time_and_review_df = delivery_time_and_review(main_df)
top_seasonal_products_df = top_3_product_sales(main_df)


st.header('Final Project Dashboard :sparkles:')
st.subheader('Sales Analysis')

# Total Sales
total_daily_sales = daily_sales_df.sum()
total_daily_sales_formatted = format_currency(total_daily_sales, "USD", locale='en_US')
st.metric("Total Sales (USD)", value=total_daily_sales_formatted)

# daily Sales Plot
fig, ax = plt.subplots(figsize=(12, 6))
ax.plot(
    daily_sales_df.index,
    daily_sales_df.values,
    marker='o',
    linewidth=2,
    color="#90CAF9"
)
ax.tick_params(axis='y', labelsize=12)
ax.tick_params(axis='x', labelsize=10)
ax.set_xlabel("Day", fontsize=12)
ax.set_ylabel("Daily Sales (USD)", fontsize=12)
st.pyplot(fig)

# Top Products Ordered
st.subheader("Top Products Ordered")
top_products = product_counts_df.sort_values(by='count', ascending=False).head(5)
colors = sns.color_palette("pastel")
fig, ax = plt.subplots(figsize=(10, 6))
ax.bar(top_products['product_category_name'], top_products['count'], color=colors)
plt.title("Top 5 Ordered Products", fontsize=14)
ax.set_xlabel("Product Category", fontsize=12)
ax.set_ylabel("Count", fontsize=12)
ax.tick_params(axis='x', labelrotation=45, labelsize=10)
ax.tick_params(axis='y', labelsize=10)
for i, v in enumerate(top_products['count']):
    ax.text(i, v + 10, str(v), ha='center', fontsize=10)
plt.tight_layout()
st.pyplot(fig)


# Payment Analytics
st.subheader("Payment Analytics")
col1, col2 = st.columns(2)

with col1:
    fig = px.pie(
        payment_percentages_df,
        values='count',  
        names=payment_percentages_df.index,
        title="Payment Method Percentages",
        hole=0.4,
    )
    fig.update_layout(
        width=300,
        height=300,
        margin=dict(l=0, r=0, b=0, t=30),
    )
    st.plotly_chart(fig)

with col2:
    fig = px.line(
        payment_trends_df,
        x=payment_trends_df.index,
        y=payment_trends_df.columns,
        labels={'x': 'Month', 'y': 'Count'},
        title="Payment Trends Over the Last Year",
    )
    fig.update_layout(
        width=500,
        height=300,
        xaxis_title="Month",
        yaxis_title="Count",
        legend_title="Payment Method",
    )
    st.plotly_chart(fig)

# City Opportunity Analysis
st.subheader("City Opportunity")
top_10_cities = city_opportunity_df.head(10)
sns.set(style='whitegrid')
plt.figure(figsize=(6, 3))
sns.barplot(x='Opportunity', y='City', hue='City', data=top_10_cities, legend=False)
plt.xlabel('Opportunity', fontsize=8)
plt.title('Top 10 Cities with Business Opportunities')
st.pyplot(plt)

# Delivery Time vs. Review Score
st.subheader("Delivery Time vs. Review Score")
fig = px.scatter(
    delivery_time_and_review_df,
    x="delivery_time",
    y="review_score",
    title="Delivery Time vs. Review Score",
    labels={"delivery_time": "Delivery Time (Days)", "review_score": "Review Score"},
    hover_name="delivery_time",
    hover_data={"delivery_time": True, "review_score": True},
)
fig.update_layout(
    xaxis_title="Delivery Time (Days)",
    yaxis_title="Review Score",
    showlegend=False,
)
st.plotly_chart(fig)

# Seasonal Sales of Top 3 Products
st.subheader("Seasonal Sales of Top 3 Products")
fig = px.line(
    top_seasonal_products_df,
    x="order_purchase_timestamp",
    y="order_item_id",
    color="product_category_name",
    title="Seasonal Sales of Top 3 Products",
    labels={"order_purchase_timestamp": "Date", "order_item_id": "Sales"},
)
fig.update_layout(
    xaxis_title="Date",
    yaxis_title="Sales",
    showlegend=True,
)
st.plotly_chart(fig)

# Copyright
st.caption('Copyright © Dicoding 2023')
