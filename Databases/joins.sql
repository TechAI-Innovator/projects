select sales.sales_id, sales_details_id,
customer_id, order_date, product_id, quantity
from sales inner join sales_details
on sales.sales_id = sales_details.sales_id;



select sales.sales_id, sales_details_id,
customers.customer_id, cusstomer_name order_date,
products.product_id, product_name, quantity
from sales inner join sales_details
on sales.sales_id = sales_details.sales_id
inner join products
on sales_details.product_id = products.product_id
inner join customers
on sales.customer_id = customers.customer_id;