import akka.actor.{ActorSystem}
import com.kleegroup.app._
import org.scalatra._
import javax.servlet.ServletContext

import scala.concurrent.duration._
import java.util.concurrent.TimeUnit
import com.github.sstone.amqp.{ChannelOwner, ConnectionOwner, Amqp}
import com.github.sstone.amqp.Amqp._
import com.rabbitmq.client.ConnectionFactory

class ScalatraBootstrap extends LifeCycle {
  val system = ActorSystem()
  val connFactory = new ConnectionFactory()

  val rabbitMQUser = System.getenv("RABBITMQ_USERNAME")
  val rabbitMQPassword = System.getenv("RABBITMQ_PASSWORD")
  val rabbitMQVhost = System.getenv("RABBITMQ_VHOST")
  val rabbitMQHost = System.getenv("RABBITMQ_HOST")

  connFactory.setUri(s"amqp://$rabbitMQUser:$rabbitMQPassword@$rabbitMQHost/$rabbitMQVhost")
  val conn = system.actorOf(ConnectionOwner.props(connFactory, 1 second))

  // Create producer
  val producer = ConnectionOwner.createChildActor(conn, ChannelOwner.props())

  // Make sure everyone is connected to broker
  waitForConnection(system, conn, producer).await(5, TimeUnit.SECONDS)


  override def init(context: ServletContext) {
    context.mount(new KleeServlet(system, producer), "/*")
  }

  override def destroy(context: ServletContext) {
  	Thread.sleep(500)
  	system.shutdown()
  }
}
