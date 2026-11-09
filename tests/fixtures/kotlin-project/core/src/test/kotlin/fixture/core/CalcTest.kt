package fixture.core

import kotlin.test.Test
import kotlin.test.assertEquals

class CalcTest {
    @Test
    fun addsTwoNumbers() {
        assertEquals(5, Calc().add(2, 3))
    }

    @Test
    fun signOfAPositiveNumber() {
        assertEquals(1, Calc().sign(7))
    }
}
