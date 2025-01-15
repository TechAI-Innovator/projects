create database franchise


create table if not exists products
(product_id varchar(10) primary key,
product_name varchar(50) not null,
stock_count int unsigned not null,
price float check (price > 0)
);

create table if not exists customersCREATE DATABASE `futa` /*!40100 DEFAULT CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci */ /*!80016 DEFAULT ENCRYPTION='N' */;

(customer_id varchar(10),
cusstomer_name varchar(100) not null,
phone_number varchar(14) not null,
email_address varchar(50) not null,
address varchar(100) not null,
primary key(customer_id)
);

create table if not exists sales
(sales_id int auto_increment primary key,
customer_id varchar(10),
order_date datetime not null,
foreign key(customer_id) references customers (customer_id)
);

create table if not exists sales_details
(sales_details_id int auto_increment primary key,
sales_id int,
product_id varchar(10),
quantity int unsigned not null,
foreign key(product_id) references products(product_id),
foreign key(sales_id) references sales(sales_id)
);

alter table sales_details
add column total float not null check (total > 0);