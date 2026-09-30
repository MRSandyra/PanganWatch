{% test prov_kab_unique(model, prov_column, kab_column) %}
-- Test: each kab/kota belongs to exactly one province
select {{ prov_column }}, {{ kab_column }}, count(*) as cnt
from {{ model }}
group by {{ prov_column }}, {{ kab_column }}
having count(*) > 1
{% endtest %}