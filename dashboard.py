import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime
import warnings
warnings.filterwarnings('ignore')

# Page configuration
st.set_page_config(
    page_title="GlobalMart Sales Dashboard",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS for better styling
st.markdown("""
    <style>
    .metric-card {
        background-color: #f0f2f6;
        padding: 20px;
        border-radius: 10px;
        border-left: 4px solid #1f77b4;
    }
    .stMetric {
        background-color: white;
        padding: 10px;
        border-radius: 5px;
    }
    </style>
""", unsafe_allow_html=True)

@st.cache_data
def load_data():
    """Load and clean the data"""
    # Load datasets
    orders = pd.read_csv('globalmart_orders.csv')
    returns = pd.read_csv('globalmart_returns.csv')
    
    return orders, returns

@st.cache_data
def clean_and_prepare_data(orders, returns):
    """Clean data and handle data quality issues"""
    
    # Create a copy to avoid modifying cached data
    orders_clean = orders.copy()
    returns_clean = returns.copy()
    
    # Data quality issues to document
    data_issues = []
    
    # 1. Handle date format inconsistencies
    # Some dates are in YYYY-MM-DD format, others in MM/DD/YYYY format
    def parse_date(date_str):
        if pd.isna(date_str):
            return pd.NaT
        try:
            # Try YYYY-MM-DD format first
            return pd.to_datetime(date_str, format='%Y-%m-%d')
        except:
            try:
                # Try MM/DD/YYYY format
                return pd.to_datetime(date_str, format='%m/%d/%Y')
            except:
                return pd.NaT
    
    orders_clean['Order_Date'] = orders_clean['Order_Date'].apply(parse_date)
    orders_clean['Ship_Date'] = orders_clean['Ship_Date'].apply(parse_date)
    
    # Document missing dates
    missing_order_dates = orders_clean['Order_Date'].isna().sum()
    missing_ship_dates = orders_clean['Ship_Date'].isna().sum()
    if missing_order_dates > 0:
        data_issues.append(f"Found {missing_order_dates} rows with missing Order_Date")
    if missing_ship_dates > 0:
        data_issues.append(f"Found {missing_ship_dates} rows with missing Ship_Date")
    
    # Remove rows with missing Order_Date (critical for analysis)
    orders_clean = orders_clean.dropna(subset=['Order_Date'])
    
    # 2. Check for duplicates
    initial_count = len(orders_clean)
    orders_clean = orders_clean.drop_duplicates()
    duplicates_removed = initial_count - len(orders_clean)
    if duplicates_removed > 0:
        data_issues.append(f"Removed {duplicates_removed} duplicate rows")
    
    # 3. Standardize Region values (check for inconsistencies)
    region_counts = orders_clean['Region'].value_counts()
    data_issues.append(f"Regions found: {', '.join(region_counts.index.tolist())}")
    
    # 4. Check for negative sales or unusual values
    negative_sales = (orders_clean['Sales'] < 0).sum()
    if negative_sales > 0:
        data_issues.append(f"Found {negative_sales} rows with negative sales")
    
    # 5. Join returns data
    # Convert Returned column to boolean
    returns_clean['Is_Returned'] = returns_clean['Returned'].apply(lambda x: True if x == 'Yes' else False)
    
    # Merge returns with orders
    orders_clean = orders_clean.merge(
        returns_clean[['Order_ID', 'Is_Returned']],
        on='Order_ID',
        how='left'
    )
    
    # Fill NaN with False for orders that weren't returned
    orders_clean['Is_Returned'] = orders_clean['Is_Returned'].fillna(False)
    
    # 6. Create additional useful columns
    orders_clean['Year'] = orders_clean['Order_Date'].dt.year
    orders_clean['Month'] = orders_clean['Order_Date'].dt.month
    orders_clean['Year_Month'] = orders_clean['Order_Date'].dt.to_period('M').astype(str)
    orders_clean['Year_Month_Date'] = pd.to_datetime(orders_clean['Year_Month'])
    
    return orders_clean, data_issues

def calculate_metrics(df):
    """Calculate key business metrics"""
    total_sales = df['Sales'].sum()
    total_profit = df['Profit'].sum()
    profit_margin = (total_profit / total_sales * 100) if total_sales > 0 else 0
    
    # Return rate: count unique orders that were returned
    total_orders = df['Order_ID'].nunique()
    returned_orders = df[df['Is_Returned'] == True]['Order_ID'].nunique()
    return_rate = (returned_orders / total_orders * 100) if total_orders > 0 else 0
    
    # Average Order Value
    avg_order_value = total_sales / total_orders if total_orders > 0 else 0
    
    return {
        'total_sales': total_sales,
        'total_profit': total_profit,
        'profit_margin': profit_margin,
        'return_rate': return_rate,
        'avg_order_value': avg_order_value,
        'total_orders': total_orders,
        'returned_orders': returned_orders
    }

# Load and clean data
orders_raw, returns_raw = load_data()
orders_df, data_issues = clean_and_prepare_data(orders_raw, returns_raw)

# Title
st.title("📊 GlobalMart Sales & Profitability Dashboard")
st.markdown("---")

# Sidebar for filters
st.sidebar.header("🔍 Filters")

# Date range filter
min_date = orders_df['Order_Date'].min().date()
max_date = orders_df['Order_Date'].max().date()

date_range = st.sidebar.date_input(
    "Select Date Range",
    value=(min_date, max_date),
    min_value=min_date,
    max_value=max_date
)

# Region filter
regions = ['All'] + sorted(orders_df['Region'].unique().tolist())
selected_region = st.sidebar.selectbox("Select Region", regions)

# Apply filters
filtered_df = orders_df.copy()

if len(date_range) == 2:
    filtered_df = filtered_df[
        (filtered_df['Order_Date'].dt.date >= date_range[0]) &
        (filtered_df['Order_Date'].dt.date <= date_range[1])
    ]

if selected_region != 'All':
    filtered_df = filtered_df[filtered_df['Region'] == selected_region]

# Calculate metrics for filtered data
metrics = calculate_metrics(filtered_df)

# KPI Cards
st.subheader("📈 Key Performance Indicators")
col1, col2, col3, col4 = st.columns(4)

with col1:
    st.metric(
        label="Total Sales",
        value=f"${metrics['total_sales']:,.0f}",
        delta=None
    )

with col2:
    st.metric(
        label="Total Profit",
        value=f"${metrics['total_profit']:,.0f}",
        delta=None
    )

with col3:
    st.metric(
        label="Profit Margin %",
        value=f"{metrics['profit_margin']:.2f}%",
        delta=None
    )

with col4:
    st.metric(
        label="Return Rate %",
        value=f"{metrics['return_rate']:.2f}%",
        delta=None
    )

st.markdown("---")

# Visualizations
col_left, col_right = st.columns(2)

# Time Series Chart - Sales and Profit over time
with col_left:
    st.subheader("📅 Sales & Profit Trend Over Time")
    
    # Aggregate by month
    monthly_data = filtered_df.groupby('Year_Month_Date').agg({
        'Sales': 'sum',
        'Profit': 'sum',
        'Order_ID': 'nunique'
    }).reset_index()
    
    fig_trend = go.Figure()
    
    fig_trend.add_trace(go.Scatter(
        x=monthly_data['Year_Month_Date'],
        y=monthly_data['Sales'],
        mode='lines+markers',
        name='Sales',
        line=dict(color='#1f77b4', width=2),
        yaxis='y'
    ))
    
    fig_trend.add_trace(go.Scatter(
        x=monthly_data['Year_Month_Date'],
        y=monthly_data['Profit'],
        mode='lines+markers',
        name='Profit',
        line=dict(color='#2ca02c', width=2),
        yaxis='y2'
    ))
    
    fig_trend.update_layout(
        xaxis_title="Month",
        yaxis=dict(title="Sales ($)", side="left"),
        yaxis2=dict(title="Profit ($)", side="right", overlaying="y"),
        hovermode='x unified',
        height=400,
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
    )
    
    st.plotly_chart(fig_trend, use_container_width=True)

# Performance by Region
with col_right:
    st.subheader("🌍 Performance by Region")
    
    region_performance = filtered_df.groupby('Region').agg({
        'Sales': 'sum',
        'Profit': 'sum',
        'Order_ID': 'nunique'
    }).reset_index()
    
    region_performance['Profit_Margin'] = (region_performance['Profit'] / region_performance['Sales'] * 100)
    region_performance = region_performance.sort_values('Profit', ascending=True)
    
    fig_region = px.bar(
        region_performance,
        x='Profit',
        y='Region',
        orientation='h',
        color='Profit_Margin',
        color_continuous_scale='RdYlGn',
        text='Profit',
        labels={'Profit': 'Total Profit ($)', 'Profit_Margin': 'Profit Margin (%)'},
        title=""
    )
    
    fig_region.update_traces(
        texttemplate='$%{text:,.0f}',
        textposition='outside',
        hovertemplate='<b>%{y}</b><br>Profit: $%{x:,.0f}<br>Profit Margin: %{customdata:.2f}%<extra></extra>',
        customdata=region_performance['Profit_Margin']
    )
    
    fig_region.update_layout(
        height=400,
        showlegend=False,
        yaxis_title="",
        xaxis_title="Total Profit ($)"
    )
    
    st.plotly_chart(fig_region, use_container_width=True)

st.markdown("---")

# Category Performance
st.subheader("📦 Performance by Category")
col_cat1, col_cat2 = st.columns(2)

with col_cat1:
    category_performance = filtered_df.groupby('Category').agg({
        'Sales': 'sum',
        'Profit': 'sum'
    }).reset_index()
    
    category_performance['Profit_Margin'] = (category_performance['Profit'] / category_performance['Sales'] * 100)
    category_performance = category_performance.sort_values('Profit_Margin', ascending=True)
    
    fig_category = px.bar(
        category_performance,
        x='Category',
        y='Profit_Margin',
        color='Profit',
        color_continuous_scale='RdYlGn',
        text='Profit_Margin',
        labels={'Profit_Margin': 'Profit Margin (%)', 'Profit': 'Total Profit ($)'},
        title="Profit Margin by Category"
    )
    
    fig_category.update_traces(
        texttemplate='%{text:.2f}%',
        textposition='outside',
        hovertemplate='<b>%{x}</b><br>Profit Margin: %{y:.2f}%<br>Total Profit: $%{customdata:,.0f}<extra></extra>',
        customdata=category_performance['Profit']
    )
    
    fig_category.update_layout(
        height=350,
        showlegend=False,
        xaxis_title="Category",
        yaxis_title="Profit Margin (%)"
    )
    
    st.plotly_chart(fig_category, use_container_width=True)

with col_cat2:
    # Sales by Category
    fig_category_sales = px.pie(
        category_performance,
        values='Sales',
        names='Category',
        title="Sales Distribution by Category",
        hole=0.4
    )
    
    fig_category_sales.update_traces(
        textposition='inside',
        textinfo='percent+label',
        hovertemplate='<b>%{label}</b><br>Sales: $%{value:,.0f}<br>Percentage: %{percent}<extra></extra>'
    )
    
    fig_category_sales.update_layout(
        height=350,
        showlegend=True
    )
    
    st.plotly_chart(fig_category_sales, use_container_width=True)

st.markdown("---")

# Additional Analysis: Discount Impact
st.subheader("💰 Discount Impact Analysis")
discount_analysis = filtered_df.groupby(pd.cut(filtered_df['Discount'], bins=[0, 0.1, 0.2, 0.3, 0.4, 1.0], labels=['0-10%', '10-20%', '20-30%', '30-40%', '40%+'])).agg({
    'Sales': 'sum',
    'Profit': 'sum',
    'Order_ID': 'nunique'
}).reset_index()

discount_analysis['Profit_Margin'] = (discount_analysis['Profit'] / discount_analysis['Sales'] * 100)

fig_discount = px.bar(
    discount_analysis,
    x='Discount',
    y='Profit_Margin',
    color='Profit',
    color_continuous_scale='RdYlGn',
    text='Profit_Margin',
    labels={'Profit_Margin': 'Profit Margin (%)', 'Discount': 'Discount Range', 'Profit': 'Total Profit ($)'},
    title="Profit Margin by Discount Range"
)

fig_discount.update_traces(
    texttemplate='%{text:.2f}%',
    textposition='outside',
    hovertemplate='<b>%{x}</b><br>Profit Margin: %{y:.2f}%<br>Total Profit: $%{customdata:,.0f}<extra></extra>',
    customdata=discount_analysis['Profit']
)

fig_discount.update_layout(
    height=350,
    showlegend=False,
    xaxis_title="Discount Range",
    yaxis_title="Profit Margin (%)"
)

st.plotly_chart(fig_discount, use_container_width=True)

st.markdown("---")

# Insights Section
st.subheader("💡 Key Insights & Recommendations")

insights = f"""
### Regional Performance Analysis
- **Best Performing Region**: {region_performance.loc[region_performance['Profit'].idxmax(), 'Region']} with ${region_performance['Profit'].max():,.0f} in profit and {region_performance.loc[region_performance['Profit'].idxmax(), 'Profit_Margin']:.2f}% profit margin
- **Region Needing Attention**: {region_performance.loc[region_performance['Profit'].idxmin(), 'Region']} with ${region_performance['Profit'].min():,.0f} in profit and {region_performance.loc[region_performance['Profit'].idxmin(), 'Profit_Margin']:.2f}% profit margin

### Category Profitability
- **Most Profitable Category**: {category_performance.loc[category_performance['Profit_Margin'].idxmax(), 'Category']} with {category_performance['Profit_Margin'].max():.2f}% profit margin
- **Least Profitable Category**: {category_performance.loc[category_performance['Profit_Margin'].idxmin(), 'Category']} with {category_performance['Profit_Margin'].min():.2f}% profit margin

### Business Recommendations
1. **Focus on High-Margin Categories**: Prioritize inventory and marketing for {category_performance.loc[category_performance['Profit_Margin'].idxmax(), 'Category']} category which shows the highest profit margins
2. **Regional Strategy Review**: Investigate why {region_performance.loc[region_performance['Profit'].idxmin(), 'Region']} region is underperforming - consider reviewing pricing strategy, discount levels, or operational costs
3. **Discount Optimization**: Analyze discount impact - high discounts (40%+) may be eroding profitability. Consider reducing excessive discounts or focusing them on high-margin products
4. **Return Rate Management**: Current return rate of {metrics['return_rate']:.2f}% should be monitored. High return rates in specific regions or categories may indicate product quality or customer satisfaction issues
5. **Average Order Value**: Current AOV of ${metrics['avg_order_value']:,.2f} - consider bundling strategies or upselling to increase order value and overall profitability
"""

st.markdown(insights)

st.markdown("---")

# Data Quality Issues Section
with st.expander("📋 Data Quality Issues Found & Resolved"):
    st.write("**Issues Identified and Addressed:**")
    for issue in data_issues:
        st.write(f"- {issue}")
    st.write("\n**Actions Taken:**")
    st.write("- Standardized date formats (handled both YYYY-MM-DD and MM/DD/YYYY formats)")
    st.write("- Removed duplicate rows to ensure accurate metrics")
    st.write("- Removed rows with missing Order_Date (critical for time-based analysis)")
    st.write("- Properly joined returns data with orders using left join")
    st.write("- Handled missing return indicators by defaulting to False")

# Footer
st.markdown("---")
st.caption("Dashboard created for GlobalMart Sales & Profitability Analysis | Data as of latest available date")
