data class Pairing(val name:String,val code:Int)
fun source(choose:Boolean):String? {if(choose)return "left";return null}
fun pair()=Pairing("left",1)
fun use(){val assigned=source(true);val count=source(false)?.length;val(name,code)=pair()}
