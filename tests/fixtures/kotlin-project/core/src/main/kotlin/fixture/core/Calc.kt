package fixture.core

class Calc {
    fun add(a: Int, b: Int): Int = a + b

    fun sign(value: Int): Int {
        if (value > 0) {
            return 1
        }
        if (value < 0) {
            return -1
        }
        return 0
    }
}
