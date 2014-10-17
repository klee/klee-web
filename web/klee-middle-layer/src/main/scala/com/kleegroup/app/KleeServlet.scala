package com.kleegroup.app

import org.scalatra._
import scalate.ScalateSupport

import _root_.akka.actor.{ActorRef, Actor, ActorSystem}
import com.github.sstone.amqp.Amqp.Publish


class KleeServlet(system:ActorSystem, producer:ActorRef) extends KleeMiddleLayerStack {

    // Index
    get("/") {
        <html>
            <body>
                <h1>Hello, world!</h1>
                Say <a href="hello-scalate">hello to Scalate</a>.
            </body>
        </html>
    }

    // Form
    get("/form") {
        <html>
            <body>
                <h1>Form</h1>
                <form action="" method="POST">
                    <input type="text" name="test" />
                    <br />
                    <br />
                    <textarea name="code"></textarea>
                    <input type="submit" name="submit" value="Submit" />
                </form>
            </body>
        </html>
    }

    post("/form") {
        val test:String = params.getOrElse("test", halt(500))
        val code:String = params.getOrElse("code", halt(500))
        producer ! Publish("", "hello", code.getBytes, properties = None, mandatory = true, immediate = false)

        <html>
            <body>
                <h1>Result</h1>
                <p>You posted: {test}</p>
                <pre>{code}</pre>
            </body>
        </html>
    }

    get("/test") {
        producer ! Publish("", "hello", "".getBytes, properties = None, mandatory = true, immediate = false)
    }

}
