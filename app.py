from pathlib import Path
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

st.set_page_config(page_title='European Bank | Churn Intelligence', page_icon='🏦', layout='wide', initial_sidebar_state='expanded')
DATA_PATH = Path(__file__).parent / 'European_Bank P2.csv'

st.markdown('''<style>
.main {background:#f6f8fc}.block-container{padding-top:1.5rem;padding-bottom:2rem}
[data-testid="stMetric"]{background:#fff;border:1px solid #e4e9f2;padding:15px 18px;border-radius:12px}
[data-testid="stMetricLabel"]{color:#5c6b82}.hero{padding:22px 26px;border-radius:16px;background:linear-gradient(120deg,#102b52,#215b91);color:white;margin-bottom:18px}
.hero h1{font-size:2rem;margin:0}.hero p{margin:8px 0 0;color:#dbeafe}
</style>''', unsafe_allow_html=True)

@st.cache_data
def load_data(path):
    df = pd.read_csv(path)
    # Normalize common binary fields while preserving the source values otherwise.
    for c in ['Exited', 'HasCrCard', 'IsActiveMember']:
        if c in df.columns:
            df[c] = pd.to_numeric(df[c], errors='coerce')
    return df

if not DATA_PATH.exists():
    st.error('Dataset not found. Upload `European_Bank P2.csv` beside `app.py` in your GitHub repository.')
    st.stop()

df = load_data(DATA_PATH)
required = {'Geography','Age','Tenure','Balance','EstimatedSalary','Exited'}
missing = required - set(df.columns)
if missing:
    st.error(f'Dataset is missing required columns: {", ".join(sorted(missing))}')
    st.stop()

st.markdown('<div class="hero"><h1>🏦 European Bank Customer Churn Dashboard</h1><p>Interactive churn monitoring • customer segments • retention opportunities</p></div>', unsafe_allow_html=True)
st.caption('Explore the supplied customer dataset. Associations shown here are descriptive and do not prove that a factor causes churn.')

with st.sidebar:
    st.header('🔎 Segment filters')
    countries = sorted(df['Geography'].dropna().astype(str).unique()) if 'Geography' in df else []
    selected_countries = st.multiselect('Geography', countries, default=countries)
    genders = sorted(df['Gender'].dropna().astype(str).unique()) if 'Gender' in df else []
    selected_genders = st.multiselect('Gender', genders, default=genders)
    age_min = int(pd.to_numeric(df['Age'], errors='coerce').min())
    age_max = int(pd.to_numeric(df['Age'], errors='coerce').max())
    age_range = st.slider('Age range', age_min, age_max, (age_min, age_max))
    tenure_min = int(pd.to_numeric(df['Tenure'], errors='coerce').min())
    tenure_max = int(pd.to_numeric(df['Tenure'], errors='coerce').max())
    tenure_range = st.slider('Tenure (years)', tenure_min, tenure_max, (tenure_min, tenure_max))
    activity_choice = st.selectbox('Activity status', ['All', 'Active members', 'Inactive members'])
    outcome_choice = st.selectbox('Customer outcome', ['All customers', 'Exited', 'Retained'])
    st.divider()
    st.caption('Filters update every KPI, chart, and customer explorer.')

f = df.copy()
f = f[f['Geography'].astype(str).isin(selected_countries)]
if 'Gender' in f: f = f[f['Gender'].astype(str).isin(selected_genders)]
f = f[pd.to_numeric(f['Age'], errors='coerce').between(*age_range)]
f = f[pd.to_numeric(f['Tenure'], errors='coerce').between(*tenure_range)]
if activity_choice == 'Active members' and 'IsActiveMember' in f: f = f[f['IsActiveMember'] == 1]
elif activity_choice == 'Inactive members' and 'IsActiveMember' in f: f = f[f['IsActiveMember'] == 0]
if outcome_choice == 'Exited': f = f[f['Exited'] == 1]
elif outcome_choice == 'Retained': f = f[f['Exited'] == 0]

if f.empty:
    st.warning('No customers match the selected filters. Adjust one or more filters in the sidebar.')
    st.stop()

n = len(f); exited = int((f['Exited'] == 1).sum()); retained = int((f['Exited'] == 0).sum())
rate = exited / n * 100 if n else 0
avg_balance = pd.to_numeric(f['Balance'], errors='coerce').mean()
avg_age = pd.to_numeric(f['Age'], errors='coerce').mean()

k1,k2,k3,k4,k5 = st.columns(5)
k1.metric('Customers in view', f'{n:,}')
k2.metric('Churn rate', f'{rate:.2f}%')
k3.metric('Exited customers', f'{exited:,}')
k4.metric('Retained customers', f'{retained:,}')
k5.metric('Average balance', f'€{avg_balance:,.0f}' if pd.notna(avg_balance) else 'N/A')
st.divider()

t_overview, t_segments, t_explorer, t_data = st.tabs(['📊 Overview', '🧭 Customer segments', '💎 High-value churn explorer', '🧪 Data quality & drill-down'])

with t_overview:
    left,right = st.columns(2)
    with left:
        st.subheader('Customer outcome')
        outcome = pd.DataFrame({'Outcome':['Retained','Exited'],'Customers':[retained,exited]})
        fig = px.pie(outcome, names='Outcome', values='Customers', hole=.62, color='Outcome', color_discrete_map={'Retained':'#2e8b72','Exited':'#e76f51'})
        fig.update_traces(textposition='inside', textinfo='percent+label')
        fig.update_layout(margin=dict(t=20,b=10,l=10,r=10), legend_title='Outcome')
        st.plotly_chart(fig, use_container_width=True)
    with right:
        st.subheader('Geography-wise churn')
        geo = f.groupby('Geography', dropna=False).agg(Customers=('Exited','size'), Exited=('Exited','sum')).reset_index()
        geo['Churn rate (%)'] = (geo['Exited']/geo['Customers']*100).round(2)
        fig = px.bar(geo, x='Geography', y='Churn rate (%)', color='Geography', text='Churn rate (%)', hover_data=['Customers','Exited'], color_discrete_sequence=px.colors.qualitative.Set2)
        fig.update_traces(texttemplate='%{text:.1f}%', textposition='outside')
        fig.update_layout(showlegend=False, yaxis_title='Churn rate (%)', xaxis_title='', margin=dict(t=20,b=10))
        st.plotly_chart(fig, use_container_width=True)
    left,right = st.columns(2)
    with left:
        st.subheader('Age group comparison')
        age_df = f.copy()
        age_df['Age group'] = pd.cut(age_df['Age'], bins=[0,25,35,45,55,65,120], labels=['≤25','26–35','36–45','46–55','56–65','66+'], include_lowest=True)
        ag = age_df.groupby('Age group', observed=False).agg(Customers=('Exited','size'), Exited=('Exited','sum')).reset_index()
        ag['Churn rate (%)'] = (ag['Exited']/ag['Customers'].replace(0, pd.NA)*100).fillna(0)
        fig = px.bar(ag, x='Age group', y='Churn rate (%)', text='Churn rate (%)', hover_data=['Customers','Exited'], color='Churn rate (%)', color_continuous_scale='Blues')
        fig.update_traces(texttemplate='%{text:.1f}%', textposition='outside'); fig.update_layout(coloraxis_showscale=False, margin=dict(t=20,b=10))
        st.plotly_chart(fig, use_container_width=True)
    with right:
        st.subheader('Tenure and churn')
        ten = f.groupby('Tenure', dropna=False).agg(Customers=('Exited','size'), Exited=('Exited','sum')).reset_index()
        ten['Churn rate (%)'] = (ten['Exited']/ten['Customers'].replace(0,pd.NA)*100).fillna(0)
        fig = px.line(ten, x='Tenure', y='Churn rate (%)', markers=True, hover_data=['Customers','Exited'])
        fig.update_traces(line=dict(width=3,color='#2878b5'))
        fig.update_layout(xaxis_title='Tenure (years)', yaxis_title='Churn rate (%)', margin=dict(t=20,b=10))
        st.plotly_chart(fig, use_container_width=True)

with t_segments:
    st.subheader('Segment drill-down')
    dimension = st.selectbox('Compare churn by', [c for c in ['Geography','Gender','IsActiveMember','HasCrCard','NumOfProducts','Tenure'] if c in f.columns], key='segment_dim')
    seg = f.groupby(dimension, dropna=False).agg(Customers=('Exited','size'), Exited=('Exited','sum'), MeanAge=('Age','mean'), MeanBalance=('Balance','mean')).reset_index()
    seg['Churn rate (%)'] = (seg['Exited']/seg['Customers']*100).round(2)
    seg[dimension] = seg[dimension].astype(str)
    a,b = st.columns([1.4,1])
    with a:
        fig = px.bar(seg.sort_values('Churn rate (%)',ascending=False), x=dimension, y='Churn rate (%)', color='Churn rate (%)', text='Churn rate (%)', hover_data=['Customers','Exited','MeanAge','MeanBalance'], color_continuous_scale='Teal')
        fig.update_traces(texttemplate='%{text:.1f}%', textposition='outside'); fig.update_layout(coloraxis_showscale=False, margin=dict(t=20,b=10))
        st.plotly_chart(fig, use_container_width=True)
    with b:
        st.markdown('**Segment summary**')
        st.dataframe(seg.sort_values('Churn rate (%)',ascending=False).style.format({'Churn rate (%)':'{:.2f}%','MeanAge':'{:.1f}','MeanBalance':'€{:,.0f}'}), use_container_width=True, hide_index=True)
    st.subheader('Age × tenure heatmap')
    heat = f.copy()
    heat['Age group'] = pd.cut(heat['Age'], bins=[0,25,35,45,55,65,120], labels=['≤25','26–35','36–45','46–55','56–65','66+'], include_lowest=True)
    heatmap = heat.pivot_table(index='Age group', columns='Tenure', values='Exited', aggfunc='mean', observed=False)*100
    fig = px.imshow(heatmap, labels=dict(x='Tenure (years)',y='Age group',color='Churn rate (%)'), aspect='auto', color_continuous_scale='RdYlBu_r', text_auto='.1f')
    st.plotly_chart(fig, use_container_width=True)

with t_explorer:
    st.subheader('High-value customer churn explorer')
    st.write('Prioritize review using balance and estimated salary thresholds. These are configurable screening rules, not a predictive model.')
    a,b = st.columns(2)
    bal = pd.to_numeric(f['Balance'], errors='coerce').fillna(0)
    sal = pd.to_numeric(f['EstimatedSalary'], errors='coerce').fillna(0) if 'EstimatedSalary' in f else pd.Series(0,index=f.index)
    with a: balance_cut = st.slider('Minimum balance (€)', 0, int(max(100000, bal.max())), int(bal.quantile(.75)), step=5000)
    with b: salary_cut = st.slider('Minimum estimated salary (€)', 0, int(max(200000, sal.max())), int(sal.quantile(.75)), step=5000)
    high = f[(pd.to_numeric(f['Balance'],errors='coerce') >= balance_cut) | (pd.to_numeric(f.get('EstimatedSalary',0),errors='coerce') >= salary_cut)].copy()
    high['Customer status'] = high['Exited'].map({1:'Exited',0:'Retained'}).fillna('Unknown')
    high['Screening reason'] = high.apply(lambda r: 'High balance and salary' if pd.notna(r.get('Balance')) and r.get('Balance',0)>=balance_cut and pd.notna(r.get('EstimatedSalary')) and r.get('EstimatedSalary',0)>=salary_cut else ('High balance' if pd.notna(r.get('Balance')) and r.get('Balance',0)>=balance_cut else 'High estimated salary'),axis=1)
    h1,h2,h3 = st.columns(3)
    h1.metric('High-value screen matches', f'{len(high):,}')
    h2.metric('Exited in this group', f'{int((high.Exited==1).sum()):,}')
    h3.metric('Group churn rate', f'{(high.Exited.mean()*100):.2f}%' if len(high) else '0.00%')
    # Sort using the underlying Exited field before selecting display columns.
    # Exited is intentionally not required in the visible table columns.
    sort_cols = [c for c in ['Exited', 'Balance'] if c in high.columns]
    sort_ascending = [False if c == 'Exited' else False for c in sort_cols]
    high_sorted = high.sort_values(sort_cols, ascending=sort_ascending) if sort_cols else high
    cols = [c for c in ['CustomerId','Geography','Age','Tenure','CreditScore','NumOfProducts','Balance','EstimatedSalary','IsActiveMember','Customer status','Screening reason'] if c in high_sorted.columns]
    st.dataframe(high_sorted[cols], use_container_width=True, hide_index=True)
    st.download_button('⬇️ Download high-value segment CSV', high_sorted[cols].to_csv(index=False).encode('utf-8'), 'high_value_churn_segment.csv', 'text/csv')
    st.caption('Use customer-level output only in authorized internal settings. Avoid exposing personal identifiers in public repositories or presentations.')

with t_data:
    st.subheader('Data quality checks')
    q1,q2,q3 = st.columns(3)
    q1.metric('Rows', f'{len(df):,}')
    q2.metric('Duplicate rows', f'{int(df.duplicated().sum()):,}')
    q3.metric('Missing cells', f'{int(df.isna().sum().sum()):,}')
    quality = pd.DataFrame({'Column':df.columns,'Data type':[str(x) for x in df.dtypes], 'Missing values':df.isna().sum().values, 'Unique values':df.nunique(dropna=True).values})
    st.dataframe(quality, use_container_width=True, hide_index=True)
    if 'NumOfProducts' in df:
        st.subheader('Product-count churn check')
        prod = df.groupby('NumOfProducts').agg(Customers=('Exited','size'),Exited=('Exited','sum')).reset_index()
        prod['Churn rate (%)'] = (prod.Exited/prod.Customers*100).round(2)
        st.dataframe(prod, use_container_width=True, hide_index=True)
        st.info('Very high churn in rare product-count groups can reflect small sample sizes or data issues. Validate those records before operational use.')
    st.subheader('Filtered customer-level data')
    safe_cols = [c for c in f.columns if c not in ['Surname']]
    st.dataframe(f[safe_cols].head(500), use_container_width=True, hide_index=True)
    st.download_button('⬇️ Download filtered dataset CSV', f[safe_cols].to_csv(index=False).encode('utf-8'), 'filtered_bank_churn_data.csv', 'text/csv')

st.divider()
st.caption(f'Source file: {DATA_PATH.name} • Showing {len(f):,} of {len(df):,} records after filters • Churn rate = exited customers / customers in current view.')
