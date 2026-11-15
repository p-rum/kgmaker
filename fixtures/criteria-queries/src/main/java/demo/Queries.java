package demo;

import jakarta.persistence.EntityManager;
import jakarta.persistence.criteria.*;
import org.springframework.data.jpa.domain.Specification;
import org.springframework.data.jpa.repository.JpaRepository;
import com.querydsl.jpa.impl.JPAQueryFactory;
import com.querydsl.core.types.Predicate;
import com.querydsl.core.types.dsl.Expressions;
import java.util.List;

public final class Queries {
    public List<Order> criteria(EntityManager em, String status) {
        CriteriaBuilder cb = em.getCriteriaBuilder();
        CriteriaQuery<Order> query = cb.createQuery(Order.class);
        Root<Order> root = query.from(Order.class);
        query.select(root).where(cb.equal(root.get("status"), status));
        return em.createQuery(query).getResultList();
    }
    public List<Order> dynamicAttribute(EntityManager em, String field, String status) {
        CriteriaBuilder cb = em.getCriteriaBuilder();
        CriteriaQuery<Order> query = cb.createQuery(Order.class);
        Root<Order> root = query.from(Order.class);
        query.select(root).where(cb.equal(root.get(field), status));
        return em.createQuery(query).getResultList();
    }
    public List<?> dynamicRoot(EntityManager em, Class<?> type) {
        CriteriaBuilder cb = em.getCriteriaBuilder();
        CriteriaQuery<?> query = cb.createQuery(type);
        query.from(type);
        return em.createQuery(query).getResultList();
    }
    public List<Order> dynamicPredicate(EntityManager em, jakarta.persistence.criteria.Predicate predicate) {
        CriteriaBuilder cb = em.getCriteriaBuilder();
        CriteriaQuery<Order> query = cb.createQuery(Order.class);
        Root<Order> root = query.from(Order.class);
        query.select(root).where(predicate);
        return em.createQuery(query).getResultList();
    }
    public Specification<Order> specification(String status) {
        return (root, query, cb) -> cb.equal(root.get("status"), status);
    }
    public Specification<Order> dynamicSpecification(String field, String status) {
        return (root, query, cb) -> cb.equal(root.get(field), status);
    }
    public List<Order> querydsl(JPAQueryFactory factory, String status) {
        QOrder order = QOrder.order;
        return factory.selectFrom(order).where(order.status.eq(status)).fetch();
    }
    public List<Order> querydslNumber(JPAQueryFactory factory, Long id) {
        QOrder order = QOrder.order;
        return factory.selectFrom(order).where(order.id.eq(id)).fetch();
    }
    public List<Order> dynamicQuerydsl(JPAQueryFactory factory, Predicate predicate) {
        QOrder order = QOrder.order;
        return factory.selectFrom(order).where(predicate).fetch();
    }
    public List<Order> dynamicQuerydslPath(JPAQueryFactory factory, String field, String status) {
        QOrder order = QOrder.order;
        return factory.selectFrom(order).where(Expressions.stringPath(order, field).eq(status)).fetch();
    }
}
interface OrderFragment { List<Order> matching(String status); }
interface OrderRepository extends JpaRepository<Order, Long>, OrderFragment {}
final class OrderFragmentImpl implements OrderFragment {
    private final EntityManager em;
    OrderFragmentImpl(EntityManager em) { this.em = em; }
    public List<Order> matching(String status) {
        CriteriaBuilder cb = em.getCriteriaBuilder();
        CriteriaQuery<Order> query = cb.createQuery(Order.class);
        Root<Order> root = query.from(Order.class);
        query.select(root).where(cb.equal(root.get("status"), status));
        return em.createQuery(query).getResultList();
    }
}
final class ExplicitSpecification implements Specification<Order> {
    public jakarta.persistence.criteria.Predicate toPredicate(Root<Order> root, CriteriaQuery<?> query, CriteriaBuilder cb) {
        return cb.equal(root.get("status"), "OPEN");
    }
}
