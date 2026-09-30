{% test bbox_indonesia(model, lat_column, lon_column) %}
-- Custom test: coordinates within Indonesia bounding box
-- lat: -11 to 6, lon: 95 to 141
select *
from {{ model }}
where {{ lat_column }} < -11
   or {{ lat_column }} > 6
   or {{ lon_column }} < 95
   or {{ lon_column }} > 141
{% endtest %}