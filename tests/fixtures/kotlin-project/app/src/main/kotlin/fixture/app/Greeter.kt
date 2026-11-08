package fixture.app

import fixture.core.Calc

class Greeter(private val calc: Calc = Calc()) {
    fun greet(name: String): String = "Hello, $name"

    fun total(values: List<Int>): Int = values.fold(0) { sum, value -> calc.add(sum, value) }
}
