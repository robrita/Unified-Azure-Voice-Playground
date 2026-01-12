# Streamlit Development Guidelines

## Chart Width Configuration

### General Streamlit Charts
For most Streamlit chart components, use `width="stretch"` instead of the deprecated `use_container_width=True`.

**Correct:**
```python
st.line_chart(data, width="stretch")
st.bar_chart(data, width="stretch")
```

**Incorrect (deprecated):**
```python
st.line_chart(data, use_container_width=True)
st.bar_chart(data, use_container_width=True)
```

### Plotly Charts (st.plotly_chart)
For `st.plotly_chart()` specifically, use the `config` parameter to specify Plotly configuration options instead of width parameters.

**Correct:**
```python
st.plotly_chart(fig, config={"responsive": True})
```

**Incorrect:**
```python
st.plotly_chart(fig, width="stretch")  # Deprecated
st.plotly_chart(fig, use_container_width=True)  # Deprecated
```

### Why This Matters
- `use_container_width=True` is deprecated across Streamlit components
- `width="stretch"` is the modern approach for general charts
- `st.plotly_chart()` uses Plotly's native configuration system via the `config` parameter
- Following these guidelines avoids deprecation warnings and ensures future compatibility
