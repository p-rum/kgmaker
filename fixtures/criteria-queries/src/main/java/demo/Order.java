package demo;

import jakarta.persistence.*;
import com.querydsl.core.annotations.QueryEntity;

@Entity
@QueryEntity
@Table(name = "orders")
public class Order {
    @Id @Column(name = "order_id") public Long id;
    @Column(name = "status") public String status;
}
