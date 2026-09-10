{{ config(tags=['ml', 'baseline']) }}

select *
from {{ ref('ml_rmsse_scale') }}
where rmsse_scale <= 0 or scale_observations <= 0
