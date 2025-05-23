select
  c.name as country_name
from countries c
where c.iso2 = %s