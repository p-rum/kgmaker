package org.kgmaker.worker

import com.intellij.psi.PsiElement
import org.jetbrains.kotlin.psi.KtFile
import org.jetbrains.kotlin.psi.KtNamedFunction
import java.nio.file.Path

/** Collect declaration diagnostics before deciding which optional witnesses can leave the worker. */
internal class KotlinDeclarationConflicts(
    private val state: State,
    requested: List<Path>,
    captured: List<KtFile>,
) {
    private val capturedPaths = captured.associate { file ->
        file.virtualFilePath to Path.of(file.virtualFilePath).toRealPath()
    }
    private val complete = capturedPaths.values.toSet() == requested.map { it.toRealPath() }.toSet()
    private val conflicting = mutableSetOf<Pair<String, Long>>()
    private val unknownSignatures = mutableSetOf<Pair<String, String>>()
    private val unknownPackages = mutableSetOf<String>()

    private fun declaration(element: PsiElement?): KtNamedFunction? =
        generateSequence(element) { it.parent }.filterIsInstance<KtNamedFunction>()
            .firstOrNull()?.takeIf { it.isTopLevel }

    fun overload(element: PsiElement, peers: List<PsiElement?>) {
        for (origin in listOf(element) + peers) {
            val function = declaration(origin) ?: continue
            val path = capturedPaths[function.containingKtFile.virtualFilePath] ?: continue
            val relative = state.root.relativize(path).toString().replace('\\', '/')
            conflicting.add(relative to function.textRange.startOffset.toLong())
        }
    }

    fun signatureError(element: PsiElement) {
        val function = declaration(element) ?: return
        val range = element.textRange
        val signatureParts = listOfNotNull(function.valueParameterList, function.receiverTypeReference,
            function.typeParameterList, function.typeConstraintList)
        if (signatureParts.any { it.textRange.contains(range) }) incomplete(function)
    }

    fun suppressedOverload(element: PsiElement) {
        val function = declaration(element)
        if (function != null && function.annotationEntries.any { it.textRange.contains(element.textRange) }) {
            incomplete(function)
            return
        }
        val file = element.containingFile as? KtFile ?: return
        if (file.fileAnnotationList?.textRange?.contains(element.textRange) == true)
            file.declarations.filterIsInstance<KtNamedFunction>().forEach(::incomplete)
    }

    fun incomplete(function: KtNamedFunction) {
        if (!function.isTopLevel || function.containingKtFile.virtualFilePath !in capturedPaths) return
        val pkg = function.containingKtFile.packageFqName.asString()
        val name = function.name
        if (name == null) unknownPackages.add(pkg) else unknownSignatures.add(pkg to name)
    }

    fun finish() {
        for (symbol in state.symbols.values) {
            val witness = symbol["kotlin_declaration"] as? Map<*, *> ?: continue
            val path = symbol["path"] as? String
            val start = (symbol["range"] as? Map<*, *>)?.get("start") as? Number
            val pkg = witness["package"] as String
            val name = witness["name"] as String
            if (!complete || path == null || start == null || (path to start.toLong()) in conflicting ||
                (pkg to name) in unknownSignatures || pkg in unknownPackages) {
                symbol.remove("kotlin_declaration")
            }
        }
    }
}
