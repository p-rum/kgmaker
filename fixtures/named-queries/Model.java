package demo;
import jakarta.persistence.*;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.data.jpa.repository.Query;
@Entity @Table(name="orders")
@NamedQueries({
 @NamedQuery(name="Order.summary", query="select new demo.Summary(o.id, o.status) from Order o where o.status=:status and o.status <> 'name=:literal'"),
 @NamedQuery(name="Order.positional", query="select o from Order o where o.id=?1"),
 @NamedQuery(name="Order.duplicate", query="select o from Order o"),
 @NamedQuery(name="Order.duplicate", query="select o from Order o where o.id=1"),
 @NamedQuery(name="Order.duplicate", query="select o from Order o where o.id=2"),
 @NamedQuery(name="Order.incomplete", query=""),
 @NamedQuery(name="Order.incomplete", query="select o from Order o"),
 @NamedQuery(name="Order.collision", query="select o from Order o"),
 @NamedQuery(name="Order.malformed", query="select o from Order o where ("),
 @NamedQuery(name="", query="select o from Order o")
})
@NamedNativeQueries({
 @NamedNativeQuery(name="Order.native", query="select id, status from orders where status=:status", resultClass=Summary.class),
 @NamedNativeQuery(name="Order.mapping", query="select * from orders", resultSetMapping="not-indexed")
})
class Order {
 @Id Long id;
 @Column String status;
}
@Entity
@NamedQuery(name="Other.first", query="select o from Order o")
@NamedQuery(name="Other.second", query="select o from Order o where o.id=:id")
@NamedNativeQuery(name="Other.native1", query="select id from orders", resultClass=Summary.class)
@NamedNativeQuery(name="Other.native2", query="select status from orders", resultClass=Summary.class)
class Other { @Id Long id; }
@Entity
@NamedQuery(name="Single.jpql", query="select o from Order o")
@NamedNativeQuery(name="Single.native", query="select id,status from orders", resultClass=Summary.class)
class Single { @Id Long id; }
class Summary { Summary(Long id, String status) {} }
interface Orders extends JpaRepository<Order, Long> {
 @Query(name="Single.jpql") Order singleJpql();
 @Query(name="Single.native") Summary singleNative();
 @Query(name="Order.summary") Summary summary(String status);
 @Query(name="Order.summary") Summary unbound(String wrong);
 @Query(name="Order.positional") Order positional(Long arbitrary);
 @Query(name="Order.positional") Order positionalUnbound();
 @Query(name="Order.native") Summary nativeResult(String status);
 @Query(name="Order.xml") Summary xml(String status);
 @Query(name="Order.xmlNative") Summary xmlNative(String status);
 @Query(name="Order.classXml") Order classXml(Long id);
 @Query(name="Other.first") Order repeatedFirst();
 @Query(name="Other.second") Order repeatedSecond(Long id);
 @Query(name="Other.native1") Summary repeatedNative1();
 @Query(name="Other.native2") Summary repeatedNative2();
 @Query(name="Order.duplicate") Order duplicate();
 @Query(name="Order.incomplete") Order incomplete();
 @Query(name="Order.collision") Order collision();
 @Query(name="Order.xmlDuplicate") Order xmlDuplicate();
 @Query(name="Order.xmlIncomplete") Order xmlIncomplete();
 @Query(name="Order.absent") Order absent();
 @Query(name="Order.malformed") Order malformed();
 @Query(name="Order.mapping") Summary unsupportedMapping();
}
