package org.kgmaker.worker

import com.fasterxml.jackson.databind.ObjectMapper
import java.nio.file.Path

private const val PROTOCOL=1
private const val VERSION="jvm-worker-1"
private fun handshake()=linkedMapOf<String,Any?>("protocol_version" to PROTOCOL,"worker" to VERSION,
    "compiler_version" to "javac-${System.getProperty("java.version")}/${KotlinFrontend.compiler}",
    "kotlin_backend" to KotlinFrontend.backend,
    "worker_jdk" to System.getProperty("java.version"),
    "capabilities" to listOf("java-attribution","typed-java-literals-bindings-v1","java-argument-parameter-bindings-v1","bytecode-asm-bundled-kotlin-2.1.10","source-ir","cha-application-classes","cha-ordered-selected-classpath") + KotlinFrontend.capabilities,
    "limitations" to KotlinFrontend.limitations + listOf(
        "CHA is conservative within ordered selected classpath and application classes; runtime/classpath completeness is not assumed.","Bytecode offsets are unavailable; instruction indexes are explicitly labelled."))

fun main() {
    val mapper=ObjectMapper()
    try {
        val raw=System.`in`.readNBytes(16*1024*1024+1)
        require(raw.size<=16*1024*1024){"request limit exceeded"}
        @Suppress("UNCHECKED_CAST")
        val request=mapper.readValue(raw,Map::class.java) as Map<String,Any?>
        require(request["protocol_version"]==PROTOCOL){"unsupported protocol version"}
        val response=when(request["operation"]) {
            "handshake" -> handshake()
            "analyze" -> {
                require(request["kotlin_version"] == null || request["kotlin_version"] == "2.1.10") {"Unsupported Kotlin compiler version"}
                val selectedBackend = if (KotlinFrontend.backend.startsWith("k2-")) "k2" else "k1"
                require(request["kotlin_backend"] == null || request["kotlin_backend"] == selectedBackend) {"Kotlin backend/distribution mismatch"}
                val state=State(request)
                @Suppress("UNCHECKED_CAST")
                val files=(request["sources"] as? List<String> ?: emptyList()).map { value ->
                    val path=state.root.resolve(value).toRealPath()
                    require(path.startsWith(state.root)){"source escapes root"}
                    path
                }
                JavaFrontend(state).analyze(files.filter {it.toString().endsWith(".java")})
                KotlinFrontend(state).analyze(files.filter {it.toString().endsWith(".kt")})
                val bytecode=Bytecode(state)
                bytecode.use {it.analyze(request["bytecode_roots"] as? List<*> ?: emptyList<Any>())}
                state.verifyInputs()
                handshake().apply {
                    put("status",if(state.diagnostics.isEmpty())"COMPLETE" else "PARTIAL")
                    put("context_id",state.context["id"])
                    put("symbols",state.symbols.values.toList())
                    put("call_sites",state.sites.sortedBy {it["id"].toString()})
                    put("bodies",state.bodies)
                    put("bytecode_cfgs",bytecode.cfgs)
                    put("facts",state.facts)
                    put("diagnostics",state.diagnostics)
                    put("coverage",mapOf("files_found" to files.size,"files_analyzed" to files.size,"methods_analyzed" to state.bodies.size,
                        "calls_found" to state.sites.size,"calls_resolved" to state.sites.count {it["evidence_kind"]=="SYMBOL_RESOLVED"},
                        "calls_unresolved" to state.sites.count {it["evidence_kind"]=="UNRESOLVED"}))
                    put("inputs",state.inputs.map {mapOf("path" to state.root.relativize(it.key).toString().replace('\\','/'),"sha256" to it.value)})
                }
            }
            else -> error("unsupported operation")
        }
        val output=mapper.writeValueAsBytes(response)
        require(output.size<=64*1024*1024){"response limit exceeded"}
        System.out.write(output);System.out.write('\n'.code)
        // Standalone Analysis API owns non-daemon IntelliJ pooled threads.
        // This protocol serves exactly one bounded request per process.
        System.out.flush()
        kotlin.system.exitProcess(0)
    }catch(error: Throwable) {
        error.printStackTrace(System.err)
        println(mapper.writeValueAsString(handshake().apply {put("status","FAILED");put("diagnostics",listOf(mapOf("code" to "WORKER_FAILED","reason" to (error.message?:error.javaClass.name))))}))
        kotlin.system.exitProcess(2)
    }
}
